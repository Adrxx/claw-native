// Level 1 world and collision entries, batch 3
// Original v1.0 entry identities remain in the dispatch table below.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

#include <cstdint>

namespace {

using claw::Run;
using claw::s32;
using namespace claw::recovered::v10;

uint32_t floatBits(float value) {
    uint32_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

float floatFromBits(uint32_t bits) {
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4cda10:
        return 4;
    case 0x4cdcb0:
        return 0;
    case 0x4cddc0:
        return 2;
    case 0x4cde00:
        return 0;
    case 0x4cde10:
        return 2;
    case 0x4cde40:
        return 0;
    case 0x4d03b0:
        return 3;
    case 0x4d0450:
        return 3;
    case 0x4d0cd0:
        return 2;
    case 0x4f4a90:
        return 0;
    default:
        return -1;
    }
}



// Clamps a coordinate to [0, limit - 1] the way the original does: negative
// goes to 0, a value at or above the limit goes to limit - 1 (signed compares).
uint32_t clampTo(uint32_t value, uint32_t limit) {
    if (s32(value) < 0)
        return 0;
    if (s32(value) >= s32(limit))
        return limit - 1;
    return value;
}

// Looks up the tile under (x, y) in the map at [self+0x5c] and asks its
// handler (vtable +0x20) about the point local to that tile. Map fields:
// +0x20 cell array, +0x24 row-offset table, +0x30 width, +0x34 height,
// +0x8c and +0x90 the log2 tile shifts. Returns 0 for an empty cell.
uint32_t probeCell(Run &run, uint32_t self, uint32_t x, uint32_t y) {
    CollisionManagerFields collision{run, self};
    if (s32(x) >= 0) {
        uint32_t widthPlaneToken = collision.tilePlane();
        CollisionTilePlaneFields widthPlane{run, widthPlaneToken};
        uint32_t width = widthPlane.widthPixels();
        x = clampTo(x, width);
    } else {
        x = 0;
    }
    if (s32(y) >= 0) {
        uint32_t heightPlaneToken = collision.tilePlane();
        CollisionTilePlaneFields heightPlane{run, heightPlaneToken};
        uint32_t height = heightPlane.heightPixels();
        y = clampTo(y, height);
    } else {
        y = 0;
    }
    uint32_t map = collision.tilePlane();
    CollisionTilePlaneFields plane{run, map};
    uint32_t shiftX = plane.columnShift();
    uint32_t shiftY = plane.rowShift();
    uint32_t cellX = uint32_t(s32(x) >> (shiftX & 31));
    uint32_t cellY = uint32_t(s32(y) >> (shiftY & 31));
    uint32_t localX = x - (cellX << (shiftX & 31));
    uint32_t localY = y - (cellY << (plane.rowShift() & 31));
    uint32_t rowStart = run.get(plane.rowOffsets() + cellY * 4);
    uint32_t cell = run.get(plane.tileIds() + (rowStart + cellX) * 4);
    if (cell == EmptyTilePattern || cell == AbsentTilePattern)
        return 0;
    uint32_t handler = run.get(collision.tileTypes() + (cell & 0xffff) * 4);
    uint32_t method = run.get(run.get(handler) + 0x20);
    return run.call(method, handler, {localX, localY});
}

// 0x4cda10. thiscall, 4 stack arguments (x, y, endX, step). Walks from x to
// endX in steps of `step` along row y, then probes endX itself. Returns 0 as
// soon as a probe answers 1, otherwise 1 unless the final probe answers 1.
uint32_t isHorizontalSpanClear(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t x = arguments[0];
    uint32_t y = arguments[1];
    uint32_t endX = arguments[2];
    uint32_t step = arguments[3];
    if (s32(x) < s32(endX)) {
        for (; s32(x) <= s32(endX); x += step) {
            uint32_t hit = probeCell(run, receiver, x, y);
            if (hit == 1)
                return 0;
        }
    } else {
        for (; s32(endX) <= s32(x); x -= step) {
            uint32_t hit = probeCell(run, receiver, x, y);
            if (hit == 1)
                return 0;
        }
    }
    uint32_t last = probeCell(run, receiver, endX, y);
    return last != 1 ? 1 : 0;
}

// 0x4cdcb0. thiscall, no arguments. Runs 0x4d2140 on each object of the
// layer array at +0x38 (count at +0x3c). That callee conditionally converts
// a layer color through the active palette; the count is re-read after it.
uint32_t visitWorldLayersForColorConversion(Run &run, uint32_t receiver, const uint32_t *arguments) {
    WorldLayerCollectionFields world{run, receiver};
    (void)arguments;
    uint32_t index = 0;
    if (s32(world.layerCount()) > 0) {
        do {
            uint32_t object = run.get(world.layers() + index * 4);
            run.call(0x4d2140, object);
            index = index + 1;
        } while (s32(index) < s32(world.layerCount()));
    }
    return 0;
}

// 0x4cddc0. thiscall, 2 ignored stack arguments. Returns the word at +0xc.
uint32_t readTileOutsideResponse(Run &run, uint32_t receiver, const uint32_t *arguments) {
    TileRectangleHandlerFields tileHandler{run, receiver};
    (void)arguments;
    return tileHandler.outsideResponse();
}

// 0x4cde00. Constant 0x14.
uint32_t readTileConstant14(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return TileConstant14;
}

// 0x4cde10. thiscall, 2 stack arguments (x, y). Bounds at +0x14 left, +0x18
// top, +0x1c right, +0x20 bottom (signed). Returns +0x10 inside, +0xc outside.
uint32_t classifyPointInTileRectangle(Run &run, uint32_t receiver, const uint32_t *arguments) {
    TileRectangleHandlerFields tileHandler{run, receiver};
    uint32_t x = arguments[0];
    uint32_t y = arguments[1];
    if (s32(x) < s32(tileHandler.left()))
        return tileHandler.outsideResponse();
    if (s32(x) > s32(tileHandler.right()))
        return tileHandler.outsideResponse();
    if (s32(y) < s32(tileHandler.top()))
        return tileHandler.outsideResponse();
    if (s32(y) > s32(tileHandler.bottom()))
        return tileHandler.outsideResponse();
    return tileHandler.insideResponse();
}

// 0x4cde40. Constant 0x28.
uint32_t readTileConstant28(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return TileConstant28;
}

// 0x4d03b0. thiscall, 3 stack arguments. Constructor. The original also links
// an exception registration through FS:[0] and unlinks it before returning;
// that frame is not part of guest data. Arguments: (+0xc, +4, +8) in the
// order they are stacked: arguments[0] -> +0xc, arguments[1] -> +4,
// arguments[2] -> +8.
uint32_t constructWorldLayer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    WorldLayerFields layer{run, receiver};
    layer.vtable(0x50e924);
    layer.unknown_0x4(arguments[1]);
    layer.flags(arguments[2]);
    layer.resourceOwner(arguments[0]);
    run.call(0x4f58ab, receiver + uint32_t(offsetof(WorldLayerLayout, unknown_0x9c)));
    layer.tileIds(0);
    layer.rowOffsets(0);
    layer.unknown_0xb0(0);
    layer.scrollScaleXBits(0x3f800000);
    layer.scrollScaleYBits(0x3f800000);
    layer.vtable(0x513d40);
    layer.clipLeft(0xffffffff);
    for (uint32_t word = 0; word < 0x19; ++word) {
        uint32_t wordToken = receiver + uint32_t(offsetof(WorldLayerLayout, unknown_0xf4)) + word * 4;
        WorldLayerTrailingWordFields trailingWord{run, wordToken};
        trailingWord.value(0);
    }
    layer.unknown_0xf4(100);
    return receiver;
}

// 0x4d0cd0. Sets pixel extents from the tile dimensions. Both shift counts
// deliberately use tileWidth, including the vertical shift, as in the original.
uint32_t configureTileDimensions(Run &run, uint32_t receiver, const uint32_t *arguments) {
    WorldLayerFields layer{run, receiver};
    uint32_t tileWidth = arguments[0];
    uint32_t tileHeight = arguments[1];
    uint32_t columns = layer.columnCount();
    layer.widthPixels(columns * tileWidth);
    uint32_t rows = layer.rowCount();
    layer.heightPixels(rows * tileHeight);
    layer.tileHeight(tileHeight);
    layer.gridBottom(tileHeight);
    layer.tileWidth(tileWidth);
    layer.gridLeft(0);
    layer.gridTop(0);
    layer.gridRight(tileWidth);
    layer.columnShift(0);
    uint32_t shifted = tileWidth;
    for (; s32(shifted) > 1; shifted = uint32_t(s32(shifted) >> 1)) {
        uint32_t shift = layer.columnShift();
        layer.columnShift(shift + 1);
    }
    layer.rowShift(0);
    shifted = tileWidth;
    for (; s32(shifted) > 1; shifted = uint32_t(s32(shifted) >> 1)) {
        uint32_t shift = layer.rowShift();
        layer.rowShift(shift + 1);
    }
    return 0;
}

// 0x4d0450. thiscall, 3 stack arguments (record, base, rect). Loads a layer
// description. Cell allocation and row-offset products establish column/row
// counts separately from each tile's pixel dimensions. Unknown words retain offset names.
uint32_t loadWorldLayerRecord(Run &run, uint32_t receiver, const uint32_t *arguments) {
    WorldLayerFields layer{run, receiver};
    WorldLayerFlagByteFields layerFlags{run, receiver};
    uint32_t record = arguments[0];
    WorldLayerRecordFields layerRecord{run, record};
    uint32_t base = arguments[1];
    uint32_t rect = arguments[2];
    InteractionRectangleFields clipRect{run, rect};
    uint32_t nameBuffer = run.automatic(-0x80);
    uint32_t outSlot = run.automatic(-0x98);
    uint32_t copiedRect = run.automatic(-0x90);
    InteractionRectangleFields copiedClipRect{run, copiedRect};
    if (layerRecord.unknown_0x0() != 0xa0)
        return 0;
    uint32_t names = layerRecord.resourceNamesOffset() + base;
    uint32_t cursor = 0;
    uint32_t index = 0;
    if (layerRecord.resourceNameCount() != 0) {
        do {
            int32_t length = 0;
            for (;;) {
                int8_t ch = int8_t(run.get8(names + cursor));
                if (ch < 0x30 && ch != 0)
                    cursor = cursor + 1;
                else
                    break;
            }
            for (;;) {
                int8_t ch = int8_t(run.get8(names + cursor));
                if (ch < 0x30)
                    break;
                run.put8(nameBuffer + uint32_t(length), uint8_t(ch));
                length = length + 1;
                cursor = cursor + 1;
            }
            run.put8(nameBuffer + uint32_t(length), 0);
            if (length > 0) {
                uint32_t resourceOwnerToken = layer.resourceOwner();
                WorldResourceOwnerFields resourceOwner{run, resourceOwnerToken};
                uint32_t table = resourceOwner.lookupOwner() + 0x10;
                run.put(outSlot, 0);
                run.call(0x4f6286, table, {nameBuffer, outSlot});
                uint32_t slot = uint32_t(int32_t(int8_t(index & 0xff)));
                uint32_t value = run.get(outSlot);
                run.call(0x4f582f, receiver + uint32_t(offsetof(WorldLayerLayout, unknown_0x9c)), {slot, value});
            }
            index = index + 1;
        } while (index < layerRecord.resourceNameCount());
    }
    uint32_t serializedFlags = layerRecord.flags();
    layer.flags(serializedFlags);
    uint32_t horizontalScrollPercent = layerRecord.scrollPercentX();
    layer.scrollPercentX(horizontalScrollPercent);
    uint32_t verticalScrollPercent = layerRecord.scrollPercentY();
    layer.scrollPercentY(verticalScrollPercent);
    layer.scrollXBits(0);
    layer.scrollYBits(0);
    layer.unknown_0x80(0xfff0bdc1);
    uint32_t serializedColumnCount = layerRecord.columnCount();
    layer.columnCount(serializedColumnCount);
    uint32_t serializedRowCount = layerRecord.rowCount();
    layer.rowCount(serializedRowCount);
    uint32_t serializedTileWidth = layerRecord.tileWidth();
    layer.tileWidth(serializedTileWidth);
    uint32_t serializedTileHeight = layerRecord.tileHeight();
    layer.tileHeight(serializedTileHeight);
    uint32_t serializedUnknown90 = layerRecord.unknown_0x90();
    layer.unknown_0x80(serializedUnknown90);
    uint32_t initialClipLeft = clipRect.left();
    layer.clipLeft(initialClipLeft);
    uint32_t initialClipTop = clipRect.top();
    layer.clipTop(initialClipTop);
    uint32_t initialClipRight = clipRect.right();
    layer.clipRight(initialClipRight);
    uint32_t bottom = clipRect.bottom();
    layer.gridLeft(0);
    layer.gridTop(0);
    uint32_t gridWidth = layer.tileWidth();
    layer.clipBottom(bottom);
    uint32_t gridHeight = layer.tileHeight();
    layer.gridRight(gridWidth);
    uint32_t pixelWidth = gridWidth * layer.columnCount();
    layer.gridBottom(gridHeight);
    uint32_t pixelHeight = gridHeight * layer.rowCount();
    layer.widthPixels(pixelWidth);
    uint32_t flags = layerFlags.flags();
    layer.heightPixels(pixelHeight);
    if ((flags & 0x10) == 0) {
        uint32_t columns = layerRecord.tileWidth();
        uint32_t rows = layerRecord.tileHeight();
        const uint32_t dimensions[2] = {columns, rows};
        configureTileDimensions(run, receiver, dimensions);
    } else {
        uint32_t list = 0;
        if (s32(layer.resourceSlotCount()) > 0)
            list = run.get(layer.resourceSlotData());
        WorldResourceListFields resources{run, list};
        uint32_t count = resources.count();
        uint32_t position = 0;
        if (s32(count) > 0) {
            uint32_t low = resources.firstIndex();
            for (; s32(position) < s32(count); position = position + 1) {
                uint32_t item = 0;
                if (!(s32(position) < s32(low)) && !(s32(position) > s32(resources.lastIndex())))
                    item = run.get(resources.items() + position * 4);
                if (item != 0) {
                    uint32_t target = run.get(resources.items() + position * 4);
                    WorldResourceDimensionsFields dimensionsRecord{run, target};
                    uint32_t columns = dimensionsRecord.tileWidth();
                    uint32_t rows = dimensionsRecord.tileHeight();
                    const uint32_t dimensions[2] = {columns, rows};
                    configureTileDimensions(run, receiver, dimensions);
                    break;
                }
            }
        }
    }
    // Copy the name string including its terminator: dwords, then bytes.
    uint32_t nameLength = 0;
    while (run.get8(record + uint32_t(offsetof(WorldLayerRecordLayout, name)) + nameLength) != 0)
        nameLength = nameLength + 1;
    nameLength = nameLength + 1;
    uint32_t source = record + uint32_t(offsetof(WorldLayerRecordLayout, name));
    uint32_t target = receiver + uint32_t(offsetof(WorldLayerLayout, name));
    for (uint32_t words = nameLength >> 2; words != 0; words = words - 1) {
        run.put(target, run.get(source));
        source = source + 4;
        target = target + 4;
    }
    for (uint32_t tail = nameLength & 3; tail != 0; tail = tail - 1) {
        run.put8(target, run.get8(source));
        source = source + 1;
        target = target + 1;
    }
    uint32_t serializedUnknown78 = layerRecord.unknown_0x78();
    layer.unknown_0x144(serializedUnknown78);
    uint32_t reloadedFlags = layerRecord.flags();
    layer.flags(reloadedFlags);
    if (clipRect.left() != 0x80000000u) {
        run.icall(0x546d58, {copiedRect, rect});
        uint32_t copiedClipLeft = copiedClipRect.left();
        layer.clipLeft(copiedClipLeft);
        uint32_t copiedClipTop = copiedClipRect.top();
        layer.clipTop(copiedClipTop);
        uint32_t copiedClipRight = copiedClipRect.right();
        layer.clipRight(copiedClipRight);
        uint32_t copiedClipBottom = copiedClipRect.bottom();
        layer.clipBottom(copiedClipBottom);
        uint32_t right = layer.clipRight();
        uint32_t width = right - layer.clipLeft() + 1;
        uint32_t bottom = layer.clipBottom();
        uint32_t height = bottom - layer.clipTop() + 1;
        layer.clipWidth(width);
        layer.clipHeight(height);
        layer.clipHalfWidth(uint32_t(s32(width) / 2));
        layer.clipHalfHeight(uint32_t(s32(height) / 2));
        run.call(0x4d0a60, receiver);
    }
    // Scroll position as floats: the x87 runs at 53-bit precision, so the
    // product is formed in binary64 and then stored as binary32.
    float scale = run.getf(0x513d70);
    uint32_t scrollPercentX = layer.scrollPercentX();
    layer.scrollScaleXBits(floatBits(float(double(s32(scrollPercentX)) * double(scale))));
    uint32_t scrollPercentY = layer.scrollPercentY();
    layer.scrollScaleYBits(floatBits(float(double(s32(scrollPercentY)) * double(scale))));
    uint32_t cellByteRows = layer.rowCount();
    uint32_t cellBytes = cellByteRows * layer.columnCount() * 4;
    uint32_t cells = run.call(0x4f63ec, 0, {cellBytes});
    uint32_t cellCountRows = layer.rowCount();
    uint32_t count = cellCountRows * layer.columnCount();
    layer.tileIds(cells);
    uint32_t cellSource = layerRecord.tileDataOffset() + base;
    uint32_t cellIndex = 0;
    if (count != 0) {
        bool continueCopy;
        do {
            uint32_t word = run.get(cellSource);
            cellSource = cellSource + 4;
            run.put(layer.tileIds() + cellIndex * 4, word);
            cellIndex = cellIndex + 1;
            uint32_t countRows = layer.rowCount();
            uint32_t countColumns = layer.columnCount();
            continueCopy = cellIndex < countRows * countColumns;
        } while (continueCopy);
    }
    uint32_t rowBytes = layer.rowCount() << 2;
    uint32_t rowTable = run.call(0x4f63ec, 0, {rowBytes});
    layer.rowOffsets(rowTable);
    uint32_t row = 0;
    if (s32(layer.rowCount()) > 0) {
        do {
            uint32_t offsets = layer.rowOffsets();
            uint32_t columns = layer.columnCount();
            run.put(offsets + row * 4, row * columns);
            row = row + 1;
        } while (s32(row) < s32(layer.rowCount()));
    }
    float scrollY = float(s32(layerRecord.startY()));
    float scrollX = float(s32(layerRecord.startX()));
    if ((layerFlags.flags() & 1) == 0) {
        uint32_t startX = layerRecord.startX();
        float scaleX = floatFromBits(layer.scrollScaleXBits());
        scrollX = float(double(s32(startX)) * double(scaleX));
        uint32_t startY = layerRecord.startY();
        float scaleY = floatFromBits(layer.scrollScaleYBits());
        scrollY = float(double(s32(startY)) * double(scaleY));
    }
    layer.scrollXBits(floatBits(scrollX));
    layer.scrollYBits(floatBits(scrollY));
    run.call(0x4d0a60, receiver);
    uint32_t extra = layerRecord.extraOffset();
    if (extra != 0) {
        uint32_t extraCount = layerRecord.extraCount();
        uint32_t loaded = run.call(0x4d1620, receiver, {base + extra, extraCount});
        if (loaded == 0)
            return 0;
    }
    return 1;
}

// 0x4f4a90. thiscall, no arguments. Clears an 8-byte element.
uint32_t clearGridElement(Run &run, uint32_t receiver, const uint32_t *arguments) {
    GridElementFields element{run, receiver};
    (void)arguments;
    element.unknown_0x0(0);
    element.unknown_0x4(0);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4cda10:
        return isHorizontalSpanClear(run, receiver, arguments);
    case 0x4cdcb0:
        return visitWorldLayersForColorConversion(run, receiver, arguments);
    case 0x4cddc0:
        return readTileOutsideResponse(run, receiver, arguments);
    case 0x4cde00:
        return readTileConstant14(run, receiver, arguments);
    case 0x4cde10:
        return classifyPointInTileRectangle(run, receiver, arguments);
    case 0x4cde40:
        return readTileConstant28(run, receiver, arguments);
    case 0x4d03b0:
        return constructWorldLayer(run, receiver, arguments);
    case 0x4d0450:
        return loadWorldLayerRecord(run, receiver, arguments);
    case 0x4d0cd0:
        return configureTileDimensions(run, receiver, arguments);
    case 0x4f4a90:
        return clearGridElement(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_world_collision_03_entry, owned, body)
