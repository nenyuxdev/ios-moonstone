"""Offline tests for the XNU payload and Moonstone boot tooling."""
from pathlib import Path
import os
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import adt
import mkadt
import mkpayload


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='moonstone-tools-')
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def run_tool(self, tool, *args):
        return subprocess.run([sys.executable, str(ROOT / 'tools' / tool), *map(str, args)],
                              capture_output=True, timeout=5)

    def payload_inputs(self):
        va = 0xfffffff007004000
        kernel = bytearray(4096)
        struct.pack_into('<8I', kernel, 0, 0xfeedfacf, 0x100000c, 0, 2, 2, 360, 0, 0)
        struct.pack_into('<II16s4Q4I', kernel, 32, 0x19, 72, b'__TEXT', va, 0x4000, 0, 4096,
                         5, 5, 0, 0)
        struct.pack_into('<4I', kernel, 104, 5, 288, 6, 68)
        struct.pack_into('<Q', kernel, 104 + 16 + 32 * 8, va + 0x100)
        kpath = self.dir / 'kernel'
        kpath.write_bytes(kernel)
        root, chosen, mmap = adt.Node(), adt.Node(), adt.Node()
        root.props = [('name', 0, b'device-tree\0')]
        chosen.props = [('name', 0, b'chosen\0'), ('dram-base', 0, struct.pack('<Q', 0x180000000)),
                        ('dram-size', 0, struct.pack('<Q', 0x100000000))]
        mmap.props = [('name', 0, b'memory-map\0')]
        root.children = [chosen]
        chosen.children = [mmap]
        apath = self.dir / 'adt'
        apath.write_bytes(adt.serialize(root))
        return kpath, apath

    def test_payload_has_eight_byte_moonstone_magic_and_boot_args(self):
        kernel, tree = self.payload_inputs()
        line = 'debug=0xc cpus=1 keepsyms=1'
        blob, info = mkpayload.build(kernel, tree, line)
        self.assertEqual(struct.unpack_from('<8sII', blob), (b'MOONXNU1', 1, 1))
        self.assertEqual(blob[0x48:0x48 + len(line) + 1], line.encode() + b'\0')
        self.assertNotIn('ramdisk', info)
        adt_offset, adt_size = struct.unpack_from('<2Q', blob, 0x20)
        parsed, _ = adt.parse(blob[adt_offset:adt_offset + adt_size])
        self.assertIsNone(parsed.children[0].children[0].prop('RAMDisk'))

    def test_payload_rejects_truncated_or_embedded_nul_args(self):
        kernel, tree = self.payload_inputs()
        for line in ('x' * 608, '測' * 203, 'cpus=8\0debug=0xc'):
            with self.subTest(line_length=len(line)), self.assertRaises(ValueError):
                mkpayload.build(kernel, tree, line)

    def test_moonstone_adt_uses_board_compatible_once(self):
        root = mkadt.build(seed=bytes(64), moonstone=True)
        props = dict((name, value) for name, _, value in root.props)
        self.assertEqual(props['compatible'].count(b'xiaomi,moonstone\0'), 1)
        self.assertEqual(props['model'], b'iPhone10,3\0')
        children = {dict((name, value) for name, _, value in child.props)['name'].rstrip(b'\0'): child
                    for child in root.children}
        chosen = dict((name, value) for name, _, value in children[b'chosen'].props)
        self.assertEqual(struct.unpack('<Q', chosen['dram-base']), (0x180000000,))
        self.assertEqual(struct.unpack('<Q', chosen['dram-size']), (0x100000000,))
        self.assertEqual(chosen['firmware-version'], b'moonstone-shim\0')
        self.assertNotIn(b'moonstone-ufs', children)
        self.assertNotIn(b'product', children)

    def test_adt_rejects_incompatible_qemu_and_midmem_options(self):
        for options in ({'qemu': True}, {'midmem': True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                mkadt.build(moonstone=True, **options)

    def test_boot_progress_patch_is_valid_and_has_milestones_21_to_30(self):
        patch = ROOT / 'xnu/patches/0012a-moonstone-boot-progress-console.patch'
        text = patch.read_text()
        self.assertIn('stage > 30', text)
        for stage in range(21, 31):
            self.assertIn(f'moonstone_early_mark({stage},', text)
        result = subprocess.run(['git', 'apply', '--numstat', str(patch)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_workflow_only_packages_kernel_candidates(self):
        workflow = (ROOT / '.github/workflows/moonstone-kernel.yml').read_text()
        script = (ROOT / 'tools/mkboot.sh').read_text()
        self.assertIn('out/moonstone-kernel.img', workflow)
        self.assertIn('out/moonstone-kernel-v4.img', workflow)
        self.assertNotIn('userspace-smoke', workflow)
        self.assertNotIn('mkinit.py', workflow)
        self.assertNotIn('--ramdisk', script)
        self.assertNotIn('rootrw=1', workflow + script)

    def test_kbuild_propagates_packer_failure(self):
        tools = self.dir / 'tools'
        tools.mkdir()
        source = ROOT / 'tools/kbuild.sh'
        (tools / 'kbuild.sh').write_text(source.read_text())
        packer = tools / 'mkboot.sh'
        packer.write_text('#!/bin/sh\necho "packer cmdline: $CMDLINE" >&2\n'
                          'echo "packer rejected input" >&2\nexit 23\n')
        packer.chmod(0o755)
        fakebin = self.dir / 'bin'
        fakebin.mkdir()
        mocks = {
            'git': 'case "$*" in\nremote*) echo https://github.com/example/audit.git;;\n'
                   '*--abbrev-ref*) echo moonstone;;\n*) echo abc;;\nesac\n',
            'gh': 'case "$*" in\n*headSha*) echo 123;;\napi*) echo xnu-kernel;;\nesac\n',
            'sleep': 'exit 0\n',
        }
        for name, body in mocks.items():
            path = fakebin / name
            path.write_text('#!/bin/sh\n' + body)
            path.chmod(0o755)
        env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ['PATH'])
        result = subprocess.run(['sh', str(tools / 'kbuild.sh'), 'audit', 'test=cpus=1'],
                                env=env, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 23)
        self.assertIn(b'cpus=1', result.stderr)
        self.assertNotIn(b'rootrw=1', result.stderr)
        self.assertIn(b'packer rejected input', result.stderr)


if __name__ == '__main__':
    unittest.main()
