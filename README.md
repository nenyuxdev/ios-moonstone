# iOS en Moonstone

Port experimental, enfocado exclusivamente en el **POCO X5 5G global**
(`moonstone`, Qualcomm `holi`, placa activa `qcom,blair-qrd`). El objetivo es
ejecutar sobre XNU el espacio de usuario de iOS 16.7.16 (20H392) del iPhone X
(`iPhone10,3` / `D22AP`). El proyecto no distribuye iOS ni el firmware de Apple.

> **Estado importante:** el usuario informó que el candidato más reciente mostró
> los marcadores 20–30, hasta `entering machine_startup`. Esto confirma que XNU
> llegó a llamar a `machine_startup`; no demuestra que esa función completara,
> que BSD montara una raíz, ni que `launchd` arrancara. El artefacto no contiene
> un root filesystem y no puede iniciar iOS. No uses instrucciones de instalación
> de otro dispositivo ni flashees imágenes de este proyecto.

## Estado actual

- El usuario confirmó que el bootloader del teléfono está desbloqueado
  oficialmente.
- El teléfono ejecuta Android 14, build
  `V816.0.26.0.UMPMIXM`, slot activo `_b`.
- Se capturó el árbol de dispositivos (FDT) activo con acceso root de KernelSU.
  La identidad observada es `MOONSTONE QRD NOPMI`, compatible con
  `qcom,blair-qrd`, `qcom,blair` y `qcom,qrd`; el ID de placa es `0x1000b, 0`.
- La generación normal de ADT, `tools/mkboot.sh`, `tools/kbuild.sh` y el
  workflow `moonstone-first-boot.yml` están fijados a Moonstone.
- El shim evita las pruebas heredadas de GPU/frecuencia, no cambia el motivo
  de reinicio en PMIC y se detiene ante un error. El primer intento usa un CPU
  y verifica EL1, MMU/caché de datos desactivadas y soporte de páginas de 16 KiB antes
  de saltar a XNU; no solicita montar ni escribir `userdata`.
- El kernel todavía se configura como `SWEET`. Los nombres y compatibilidades
  SWEET/Sunstone que usan el kernel, los parches y el shim se conservan
  deliberadamente: no son solo etiquetas y reemplazarlos sin portar cada
  consumidor rompería la compatibilidad.
- XNU se compiló y se empaquetó el candidato diagnóstico del commit `ac3a258`
  (workflow `42176438438`). El usuario informó que el dispositivo mostró los
  marcadores 20–30, incluido `SWEET EARLY 30: entering machine_startup`.
  El 30 se imprime justo antes de llamar a `machine_startup`; no acredita el
  progreso posterior dentro de esa función ni un arranque de BSD/iOS.
- Se reportó una escritura manual del candidato v3 a `boot_b`; el dispositivo
  quedó en el marcador 20. Luego se probó el candidato diagnóstico hasta el
  marcador 30. El estado actual del teléfono y su slot no se han vuelto a
  verificar; esto no es un procedimiento de instalación.
- El usuario no autoriza borrar datos. No escribir `userdata` ni recomendar
  hacerlo: el port no tiene aún una ruta externa/no destructiva para alojar el
  root filesystem de iOS.

## Hardware Moonstone confirmado

Datos del FDT activo y de `/proc/iomem`:

| Recurso | Evidencia | Situación para el port |
| --- | --- | --- |
| Placa | `MOONSTONE QRD NOPMI`; `qcom,blair-qrd`; `qcom,msm-id = 0x1fb, 0x10000`; board ID `0x1000b, 0` | Identidad activa; no inferirla del índice de DTBO |
| RAM | Bancos `0x80000000 + 0x3bb00000`, `0xc0000000 + 0xc0000000`, `0x180000000 + 0x100000000` | El perfil ADT inicial selecciona solo el banco superior de 4 GiB; falta validar reservas y allocator de XNU |
| CPU | 8 nodos Kryo, MPIDR `0x0` a `0x700` | La topología visible está identificada; características/arranque SMP requieren validación |
| GIC | GICv3: distribuidor `0x0f200000`, redistribuidores `0x0f240000` | Direcciones observadas; no prueban inicialización de interrupciones en XNU |
| UFS | Controlador en `0x04804000`, estado `ok` | Activo en Android; el driver y root device de XNU no están validados |
| GPU | Adreno A619 Holi `0x05900000`; SMMU KGSL `0x05940000` | Falta integración de clocks, energía, SMMU, reset y renderizado |
| Pantalla | SDE `0x05e00000`, DSI `0x05e94000`, PHY `0x05e94900`; panel 1080×2400 a 120 Hz | Panel DSC M17; no reutilizar timing ni supuestos de Sunstone |
| Táctil | FocalTech por I²C, dirección `0x38` | El controlador Goodix del port de referencia no corresponde |
| IPCC | `0x00208000`, IRQ 334 | Recursos identificados; falta validar los clientes del módem/WLAN |
| Reservas | SMEM `0x80900000`/2 MiB; WLAN MSA `0x86500000`/2 MiB; `mpss_wlan` `0x8b800000`/256 MiB; splash `0x85200000`/12 MiB; ramoops `0xd0000000`/2 MiB | No entregar estas regiones al allocator sin validar el FDT completo |

El FDT muestra RAM en tres bancos; `/proc/iomem` informa System RAM desde
`0xf6400000` hasta `0x27fffffff` en la región superior. El ADT sintético no es
una copia íntegra del FDT de Android y no representa aún todos sus recursos.
La selección del banco superior evita asumir que las regiones inferiores están
disponibles, pero igualmente necesita revisión antes de cualquier arranque.

## Imágenes Android inspeccionadas

Los siguientes hashes identifican los archivos examinados, no demuestran por sí
solos que todos provengan de un único paquete ROM coincidente:

| Archivo | SHA-256 | Formato observado |
| --- | --- | --- |
| `vendor_boot.img` | `065eee6c89f644bf9d5fbc29b3f11e4db53c3c5d32703b5e61156321637c0c74` | Android vendor boot v3 |
| `dtbo.img` | `dca0e7af63a4bc003c78475f097bdd49a17e2f33f12998f6c7d31f31a07aa529` | Tabla DT v0, 29 overlays |
| `boot.img` | `be8e93591a8a46f952663571a1c0553e0f00d5cfeff4927d231de08249828bdf` | Android boot v3 |
| `vendor.img` | `7cd4f5991fe99a50a1f9aa103afa98518c53ce94d4a86a6d9926c29426b7a5ee` | EROFS |
| `odm.img` | `76f32c97d11424f396a03d5961a8b885e8b2f41141226e857a30c0a23d0bc836` | EROFS |

`vendor.img` y `odm.img` contienen la huella Android 14
`POCO/moonstone_p_global/moonstone:14/.../V816.0.26.0.UMPMIXM`. En cambio,
`boot.img` declara Android 11 (`POCO/moonstone/moonstone:11`) aunque comparte
el identificador incremental. Hasta verificar metadatos del paquete ROM, no
tratar ese `boot.img` como la imagen activa del teléfono.

## Qué falta

1. Validar las reservas de memoria y el rango elegido por el ADT frente a XNU,
   el shim y sus asignadores físicos.
2. Seguir validando el bootstrap después de `machine_startup`: el marcador 30
   prueba que se llegó a la llamada, no que `kernel_bootstrap` o BSD terminaran.
3. Adaptar y probar el driver de pantalla DSC M17 y el panel 1080×2400.
4. Portar el controlador táctil FocalTech; no asumir compatibilidad con Goodix.
5. Validar UFS/root, GPU A619, energía/reguladores, batería, módem y WLAN con
   el FDT activo y firmware de la misma versión.
6. Resolver la diferencia de versión entre `boot.img` y las imágenes vendor/ODM.
7. El último candidato alcanzó la llamada a `machine_startup`; falta determinar
   hasta dónde continúa el bootstrap antes de BSD y del montaje de raíz.
8. No existe una raíz de iOS en el artefacto de arranque. `tools/mkiosroot.sh`
   crea una imagen HFS+ de 16 GiB a partir de un IPSW, y el driver UFS de XNU
   puede leer una partición GPT nombrada; por defecto, esa partición es
   `userdata`. Usarla requeriría reemplazar sus datos, opción que el usuario
   rechazó. No hay actualmente una vía externa/no destructiva validada.
9. Para seguir validando sin tocar almacenamiento, el workflow se modificó
   para producir un candidato separado `moonstone-userspace-smoke` con un
   pequeño ramdisk ejecutable en memoria (`rd=md0`). Está pensado para comprobar
   el montaje mockfs y la ejecución del init de prueba; aún requiere build y
   prueba, no contiene iOS y no valida el montaje de UFS.

## Arranque previsto (aún no validado)

La ruta que se está investigando es:

```text
Bootloader Xiaomi
  -> shim temporal en formato Android boot
     -> XNU + ADT sintético Moonstone + argumentos de arranque
        -> controlador UFS y volumen raíz de iOS
           -> dyld -> launchd -> servicios de iOS
```

Esta es una arquitectura objetivo, no un procedimiento de instalación ni una
garantía de que el teléfono arranque. No ejecutar `fastboot flash userdata` ni
otros comandos de escritura: además de no estar validados, podrían borrar datos.
El usuario no quiere perder datos; no proponer particionar, formatear ni
reemplazar `userdata`. El siguiente trabajo debe limitarse a validar el avance
posterior a `machine_startup` y buscar una fuente de raíz externa que no requiera
escrituras en el almacenamiento interno.

## Construcción y pruebas disponibles

El workflow manual `.github/workflows/moonstone-first-boot.yml` compila XNU
con la configuración SWEET compatible y produce candidatos Android boot v3 y
v4: el diagnóstico básico y un smoke test aislado de userspace con ramdisk
pequeño. No descarga el IPSW, no genera un root filesystem de iOS ni tiene pasos
de instalación/flash. También se puede empaquetar un kernel ya compilado:

```sh
tools/mkboot.sh RUTA_AL_KERNEL [RUTA_DE_SALIDA]
```

Los argumentos seguros predeterminados son `debug=0xc cpus=1 keepsyms=1
-noprogress wdt=-1 sweetgpu=0 sweetfb_flip=0`: no incluyen `rd=ufsroot0`,
`rootrw=1` ni inicialización de GPU. Con el artefacto descargado y el teléfono
conectado por USB:

En el firmware probado, `fastboot boot` respondió `unknown command`; por tanto,
no es un método disponible confirmado para este dispositivo. `fastboot flash`
es una escritura persistente, no una prueba temporal. No uses instrucciones
de flash de este README ni escribas un root filesystem en `userdata`. Las
imágenes v3/v4 solo describen dos formatos de cabecera; cambiar de formato no
resuelve un bloqueo dentro del kernel. Sin root iOS no llegará a `launchd` ni
a la interfaz.

Comprobaciones offline de herramientas:

```sh
python3 -m unittest discover -s tests -p 'test_tools.py'
python3 tests/check-project.py
```

La prueba GPU anterior del repositorio no forma parte del primer arranque y no
demuestra funcionamiento en Moonstone.

## Estructura del repositorio

| Ruta | Función |
| --- | --- |
| `xnu/patches/` | Serie de parches XNU y drivers heredados |
| `xnu/patches-topaz/`, `xnu/patches-unused/` | Parches de referencia/no incluidos automáticamente en el build activo |
| `shim/` | Shim de arranque, MMU, carga, consola y código de hardware |
| `tools/mkadt.py` | Generador ADT Moonstone (QEMU queda como modo de prueba separado) |
| `tools/mkpayload.py` | Empaqueta kernel, ADT y argumentos |
| `tools/mkboot.sh` | Construye imágenes temporales de primer arranque Moonstone |
| `tools/kbuild.sh` | Orquesta la obtención del kernel CI y su empaquetado |
| `xnu/patches/0012a-sweet-boot-progress-console.patch` | Conserva la consola temprana y añade hitos después de `kprintf` |
| `tools/mkiosroot.sh` | Construcción del volumen raíz desde imágenes IPSW |
| `tests/` | Pruebas offline y comprobaciones del código/herramientas |
| `.github/workflows/` | Workflows de kernel, primer arranque Moonstone y herramientas |
| `drop/` | Archivos auxiliares que pueden incluirse en un ramdisk |

No añadir al repositorio backups de particiones, árboles FDT del dispositivo,
imágenes de recuperación, firmware propietario, rootfs ni artefactos generados.
Pueden contener datos únicos del teléfono o contenido propietario.

## Identificadores técnicos heredados

Los nombres `SWEET`, `sweet-*`, `sweet_*`, `xiaomi,sweet`, `qcom,kryo470` y
otros marcadores similares siguen apareciendo en el ABI entre el ADT sintético,
los parches XNU y el shim. Se conservan intencionalmente hasta que exista una
migración coordinada y probada de todos sus consumidores. Las etiquetas de
empaquetado nuevas dicen Moonstone, pero eso **no** significa que el código
heredado ya sea un port completo.

El proyecto está dedicado a Moonstone, pero no afirma ser oficial de Xiaomi o
Apple ni el primer intento mundial: no hay verificación independiente para
esas afirmaciones.

## Créditos y licencias

El proyecto utiliza componentes abiertos de Apple/XNU y otras herramientas de
terceros indicadas en sus fuentes y workflows. iOS y el firmware de Xiaomi son
propietarios y no se distribuyen en este repositorio. Revisa las licencias de
cada dependencia antes de redistribuir artefactos.
