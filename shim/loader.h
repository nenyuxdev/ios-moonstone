#pragma once
#include <stdint.h>

/* Boot the MOONXNU1 payload found by the shim; returns only on error. */
const char *loader_boot(uintptr_t dtb);
