#pragma once
#include <stdint.h>
namespace claw { class Run; }
namespace claw::state_registry {
uint32_t grow(Run &run, uint32_t table, uint32_t key, uint32_t margin);
uint32_t find(Run &run, uint32_t table, uint32_t key);
uint32_t insert(Run &run, uint32_t table, uint32_t key, uint32_t value);
uint32_t differingBit(Run &run, uint32_t first, uint32_t second);
uint32_t stringIndex(Run &run, uint32_t table, uint32_t key);
// Registration preserves physical child-call boundaries. nameMode/tableMode:
// 0 = inline index algorithm; 1 = original 441030 index accessor;
// nameMode 2 = owned 406020 index accessor, including CString construction.
// Each name mode constructs newly exposed CString cells exactly once.
// Inline error modes: 1 = original 406da0 error helper; otherwise pass the
// original continuation PC for the 4db5f0 diagnostic accessor. Zero is valid
// only when growth cannot fail. Later groups must supply their own source PCs.
uint32_t registerBinding(Run &run, uint32_t table, uint32_t literal, uint32_t callback,
                         uint32_t nameMode = 0, uint32_t tableMode = 0,
                         uint32_t nameErrorMode = 0, uint32_t tableErrorMode = 0);
}
