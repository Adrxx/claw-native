"""Bounded I/O for local discovery artifacts (not admission evidence).

Traces remain ordinary JSON, compressed with gzip. Arrays are decoded one row
at a time; the two large event arrays are replayable streams. Hashes refer to
the uncompressed bytes, so lossless compression preserves existing references.
Checkpoints use independent pickle records and 1 MiB memory chunks. Only local,
trusted checkpoints may be opened (pickle is not an interchange format).
"""
import gzip
import hashlib
import itertools
import json
import os
import pickle
import shutil
import tempfile
from array import array
from pathlib import Path

CHUNK = 1024 * 1024
LARGE_ARRAYS = {'physical_events', 'math_events'}
CHECKPOINT_MAGIC = b'CLAW-CHECKPOINT-4\n'


class EventLog(list):
    """Append-only disk log with the tracer's outstanding callback rows live.

Ordinary fixture rows finish changing before the next append. Vector/qsort
and enumeration rows can change across callbacks, so retain those dictionaries
by identity. The remaining memory is one row and an eight-byte offset per row.
Temporary files close automatically when the log is released.
"""
    def __init__(self, rows=()):
        self.stream = tempfile.TemporaryFile()
        self.offsets = array('Q')
        self.live = {}
        self.pending = None
        self.extend(rows)

    def append(self, row):
        if self.pending is not None:
            index, previous = self.pending
            self.stream.seek(0, 2)
            self.offsets[index] = self.stream.tell()
            pickle.dump(previous, self.stream, protocol=pickle.HIGHEST_PROTOCOL)
        self.pending = None
        index = len(self.offsets)
        self.offsets.append(0)
        if ('completed' in row or row.get('service') == 'IDirectDraw::EnumDisplayModes'):
            self.live[index] = row
        else:
            self.pending = index, row

    def extend(self, rows):
        for row in rows:
            self.append(row)

    def __len__(self):
        return len(self.offsets)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        if index in self.live:
            return self.live[index]
        if self.pending is not None and index == self.pending[0]:
            return self.pending[1]
        self.stream.seek(self.offsets[index])
        return pickle.load(self.stream)

    def __iter__(self):
        for index in range(len(self)):
            yield self[index]

    def __reversed__(self):
        for index in range(len(self)-1, -1, -1):
            yield self[index]

    def __eq__(self, other):
        return isinstance(other, (list, tuple)) and len(self) == len(other) and all(
            a == b for a, b in zip(self, other))

    def __ne__(self, other):
        return not self == other

    def __reduce_ex__(self, protocol):
        raise TypeError('Event logs require the streaming checkpoint writer')

    def close(self):
        self.stream.close()


def stored_path(path):
    path = Path(path)
    return path if path.exists() else Path(str(path) + '.gz')


def exists(path):
    return stored_path(path).exists()


def open_artifact(path, mode='rb'):
    path = stored_path(path)
    return gzip.open(path, mode) if path.suffix == '.gz' else path.open(mode)


def fingerprint(path):
    with open_artifact(path) as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class _JSONReader:
    def __init__(self, stream):
        self.stream, self.buffer, self.position = stream, '', 0
        self.decoder = json.JSONDecoder()
        self.eof = False

    def fill(self):
        self.buffer = self.buffer[self.position:]
        self.position = 0
        more = self.stream.read(65536)
        self.buffer += more
        self.eof = not more

    def peek(self):
        while True:
            while self.position < len(self.buffer) and self.buffer[self.position].isspace():
                self.position += 1
            if self.position < len(self.buffer):
                return self.buffer[self.position]
            if self.eof:
                return ''
            self.fill()

    def take(self, token):
        if self.peek() != token:
            raise ValueError(f'Expected JSON {token!r}, got {self.peek()!r}')
        self.position += 1

    def value(self):
        self.peek()
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
                # A number at the buffer boundary may continue in the next chunk.
                if end == len(self.buffer) and not self.eof:
                    self.fill()
                    continue
                if (isinstance(value, (int, float)) and not isinstance(value, bool)
                        and end < len(self.buffer) and self.buffer[end] not in ' \t\r\n,]}'):
                    if self.eof:
                        raise ValueError('Invalid JSON number')
                    self.fill()
                    continue
                self.position = end
                return value
            except json.JSONDecodeError:
                if self.eof:
                    raise
                self.fill()


def trace_rows(path):
    """Yield (field, kind, value), never materializing a top-level array."""
    with open_artifact(path, 'rt') as stream:
        reader = _JSONReader(stream)
        reader.take('{')
        if reader.peek() != '}':
            while True:
                key = reader.value()
                if not isinstance(key, str):
                    raise ValueError('Trace field must be a string')
                reader.take(':')
                if reader.peek() == '[':
                    reader.take('[')
                    yield key, 'array', None
                    if reader.peek() != ']':
                        while True:
                            yield key, 'item', reader.value()
                            if reader.peek() != ',':
                                break
                            reader.take(',')
                    reader.take(']')
                else:
                    yield key, 'value', reader.value()
                if reader.peek() != ',':
                    break
                reader.take(',')
        reader.take('}')
        if reader.peek():
            raise ValueError('Trailing trace data')


class TraceArray(list):
    """Replayable JSON array; list subclass so json.dump streams its iterator."""
    def __init__(self, path, key, length):
        self.path, self.key, self.length = Path(path), key, length

    def __len__(self):
        return self.length

    def __iter__(self):
        for key, kind, value in trace_rows(self.path):
            if key == self.key and kind == 'item':
                yield value

    def __getitem__(self, index):
        if isinstance(index, slice):
            return list(itertools.islice(iter(self), *index.indices(len(self))))
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return next(itertools.islice(iter(self), index, None))

    def __eq__(self, other):
        if not isinstance(other, (list, tuple)) or len(self) != len(other):
            return False
        return all(a == b for a, b in zip(self, other))

    def __ne__(self, other):
        return not self == other


def read_trace(path):
    result, counts = {}, {}
    for key, kind, value in trace_rows(path):
        if kind == 'array':
            result[key] = []
            counts[key] = 0
        elif kind == 'item':
            counts[key] += 1
            if key not in LARGE_ARRAYS:
                result[key].append(value)
        else:
            result[key] = value
    for key in LARGE_ARRAYS & counts.keys():
        result[key] = TraceArray(stored_path(path), key, counts[key])
    return result


def _atomic_gzip(path, writer):
    path = Path(path)
    target = path if path.suffix == '.gz' else Path(str(path) + '.gz')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix=target.name + '.')
    try:
        with os.fdopen(fd, 'wb') as raw:
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                writer(stream)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    if path != target and path.exists():
        path.unlink()
    return target


def write_trace(path, report):
    import io
    def write(stream):
        text = io.TextIOWrapper(stream, encoding='utf-8')
        try:
            json.dump(report, text, indent=2)
            text.write('\n')
            text.flush()
        finally:
            text.detach()
    return _atomic_gzip(path, write)


def compress_trace(path):
    """Lossless migration: verify uncompressed SHA before removing the source."""
    path = Path(path)
    if path.suffix == '.gz':
        return path
    digest = fingerprint(path)
    target = Path(str(path) + '.gz')
    # Pass the target so _atomic_gzip leaves the source until verification.
    def copy(stream):
        with path.open('rb') as source:
            shutil.copyfileobj(source, stream, CHUNK)
    _atomic_gzip(target, copy)
    if fingerprint(target) != digest:
        raise ValueError('Trace compression changed its contents')
    path.unlink()
    return target


def save_checkpoint(path, payload, machine):
    """Serialize the state once; never copy the complete emulator address space."""
    payload = dict(payload)
    state = payload['state'] = dict(payload.get('state', {}))
    logs = {key: state.pop(key) for key in list(state) if isinstance(state[key], EventLog)}
    payload['streamed_logs'] = {key: len(rows) for key, rows in logs.items()}
    def write(stream):
        stream.write(CHECKPOINT_MAGIC)
        with tempfile.TemporaryFile() as header:
            pickle.dump(payload, header, protocol=pickle.HIGHEST_PROTOCOL)
            stream.write(header.tell().to_bytes(8, 'little'))
            header.seek(0)
            shutil.copyfileobj(header, stream, CHUNK)
        for rows in logs.values():
            for row in rows:
                data = pickle.dumps(row, protocol=pickle.HIGHEST_PROTOCOL)
                stream.write(len(data).to_bytes(8, 'little'))
                stream.write(data)
        for start, end, _ in machine.mem_regions():
            for address in range(start, end + 1, CHUNK):
                data = bytes(machine.mem_read(address, min(CHUNK, end + 1 - address)))
                pickle.dump((address, data), stream, protocol=pickle.HIGHEST_PROTOCOL)
        pickle.dump(None, stream)
    return _atomic_gzip(path, write)


def load_checkpoint(path):
    """Read the header only; memory is loaded after the caller validates it."""
    with open_artifact(path) as stream:
        if stream.read(len(CHECKPOINT_MAGIC)) != CHECKPOINT_MAGIC:
            raise ValueError('Legacy checkpoint: migrate it with Tests.NativeLevels.storage first')
        if len(stream.read(8)) != 8:
            raise ValueError('Truncated checkpoint header')
        payload = pickle.load(stream)
        for key, count in payload.pop('streamed_logs', {}).items():
            rows = payload['state'][key] = EventLog()
            for _ in range(count):
                size = stream.read(8)
                if len(size) != 8:
                    raise ValueError('Truncated checkpoint event length')
                length = int.from_bytes(size, 'little')
                data = stream.read(length)
                if len(data) != length:
                    raise ValueError('Truncated checkpoint event')
                rows.append(pickle.loads(data))
        return payload


def restore_memory(path, machine):
    with open_artifact(path) as stream:
        if stream.read(len(CHECKPOINT_MAGIC)) != CHECKPOINT_MAGIC:
            raise ValueError('Unsupported checkpoint format')
        size = stream.read(8)
        if len(size) != 8:
            raise ValueError('Truncated checkpoint header')
        # The small header contains counts of separately streamed event rows.
        # It no longer contains either large event list or emulator memory.
        header = pickle.load(stream)
        for count in header.get('streamed_logs', {}).values():
            for _ in range(count):
                size = stream.read(8)
                if len(size) != 8:
                    raise ValueError('Truncated checkpoint event length')
                remaining = int.from_bytes(size, 'little')
                while remaining:
                    data = stream.read(min(CHUNK, remaining))
                    if not data:
                        raise ValueError('Truncated checkpoint event')
                    remaining -= len(data)
        del header
        while True:
            row = pickle.load(stream)
            if row is None:
                if stream.read(1):
                    raise ValueError('Trailing checkpoint data')
                return
            machine.mem_write(*row)


def migrate_checkpoint(path):
    """One-time migration of a trusted legacy snapshot, without read_bytes/dumps."""
    path = Path(path)
    with path.open('rb') as stream:
        payload = pickle.load(stream)
    memory = payload.pop('memory')
    for key in LARGE_ARRAYS:
        if key in payload.get('state', {}):
            payload['state'][key] = EventLog(payload['state'][key])
    class Memory:
        def mem_regions(self):
            return [(a, a + len(data) - 1, 0) for a, data in memory]

        def mem_read(self, address, size):
            for base, data in memory:
                if base <= address < base + len(data):
                    return data[address-base:address-base+size]
            raise ValueError('Missing checkpoint region')
    memory_source = Memory()
    target = save_checkpoint(Path(str(path) + '.gz'), payload, memory_source)
    if load_checkpoint(target) != payload:
        raise ValueError('Checkpoint migration changed its state')
    class VerifyMemory:
        def mem_write(self, address, data):
            if memory_source.mem_read(address, len(data)) != data:
                raise ValueError('Checkpoint migration changed memory')
    restore_memory(target, VerifyMemory())
    path.unlink()
    return target


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2] / 'work'
    for path in args.paths:
        if not path.resolve().is_relative_to(root.resolve()):
            parser.error('Artifacts must stay under work/')
        output = migrate_checkpoint(path) if path.suffix == '.pkl' else compress_trace(path)
        print(json.dumps(dict(path=str(output), bytes=output.stat().st_size)))
