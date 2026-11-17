"""Minimal, safe reader for Ren'Py RPA-3.0 archives."""
import io
import pickle
import zlib
from collections import OrderedDict
from pathlib import Path, PurePosixPath

MAX_INDEX_BYTES = 64 * 1024 * 1024
MAX_ENTRY_BYTES = 64 * 1024 * 1024
MAX_ALL_ENTRY_BYTES = 4 * 1024 * 1024 * 1024
COPY_CHUNK = 1024 * 1024
INDEX_CHUNK = 64 * 1024
INDEX_CACHE_LIMIT = 64
INDEX_CACHE_BYTES = 16 * 1024 * 1024
SCRIPT_SUFFIXES = (".rpy", ".rpyc", ".rpym", ".rpymc")
_INDEX_CACHE = OrderedDict()
_INDEX_CACHE_BYTES = 0


class RPAError(Exception):
    pass


class _SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError("RPA index classes are not allowed")


def _parse_index(path):
    try:
        with open(path, "rb") as fh:
            header = fh.readline(80).decode("ascii", "ignore").strip()
            parts = header.split()
            if len(parts) < 3 or parts[0] != "RPA-3.0":
                return {}, 0, 0
            try:
                offset = int(parts[1], 16)
                key = int(parts[2], 16)
            except ValueError:
                return {}, 0, 0
            fh.seek(offset)
            decompressor = zlib.decompressobj()
            chunks = []
            total = 0
            while True:
                block = fh.read(INDEX_CHUNK)
                if not block:
                    break
                while block:
                    remaining = MAX_INDEX_BYTES - total
                    if remaining <= 0:
                        return {}, 0, 0
                    data = decompressor.decompress(block, remaining)
                    if data:
                        chunks.append(data)
                        total += len(data)
                    block = decompressor.unconsumed_tail
                    if decompressor.eof:
                        break
                if decompressor.eof:
                    break
            if not decompressor.eof:
                return {}, 0, 0
            index = _SafeUnpickler(
                io.BytesIO(b"".join(chunks)), encoding="bytes").load()
            return index, key, total
    except Exception:
        return {}, 0, 0


def _read_index(path):
    global _INDEX_CACHE_BYTES
    path = Path(path)
    try:
        stat = path.stat()
    except OSError:
        return {}, 0
    cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
    cached = _INDEX_CACHE.get(cache_key)
    if cached is not None:
        _INDEX_CACHE.move_to_end(cache_key)
        return cached[0], cached[1]
    result = _parse_index(path)
    _INDEX_CACHE[cache_key] = result
    _INDEX_CACHE_BYTES += result[2]
    _trim_index_cache()
    return result[0], result[1]


def _trim_index_cache():
    global _INDEX_CACHE_BYTES
    while _INDEX_CACHE and (len(_INDEX_CACHE) > INDEX_CACHE_LIMIT or
                            _INDEX_CACHE_BYTES > INDEX_CACHE_BYTES):
        _key, value = _INDEX_CACHE.popitem(last=False)
        _INDEX_CACHE_BYTES -= value[2]


def _name(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return value if isinstance(value, str) else ""


def _entry(values, key):
    if not isinstance(values, (list, tuple)) or not values:
        return None
    entry = values[0]
    if not isinstance(entry, (list, tuple)):
        entry = values
    if len(entry) == 2:
        offset, length = entry
        prefix = key
    else:
        offset, length, prefix = entry[:3]
        if isinstance(prefix, bytes):
            prefix = int.from_bytes(prefix, "big") if prefix else key
        elif not prefix:
            prefix = key
        prefix = int(prefix)
    return int(offset) ^ prefix, int(length) ^ prefix


def _relative(name):
    path = PurePosixPath(name.replace("\\", "/"))
    if (not path.parts or path.is_absolute() or
            any(part in ("", ".", "..") or ":" in part
                for part in path.parts)):
        raise RPAError("Unsafe path in RPA: %s" % name)
    return Path(*path.parts)


def entry_names(path):
    index, _key = _read_index(path)
    if not isinstance(index, dict):
        return []
    return sorted(name for name in map(_name, index) if name)


def script_names(path):
    return [name for name in entry_names(path)
            if name.lower().endswith(SCRIPT_SUFFIXES)]


def has_scripts(path):
    return bool(script_names(path))


def extract_scripts(path, destination):
    path = Path(path)
    destination = Path(destination).resolve()
    index, key = _read_index(path)
    if not isinstance(index, dict) or not index:
        raise RPAError("Could not read RPA-3.0 archive: %s" % path.name)
    extracted = 0
    with open(path, "rb") as fh:
        for raw_name, values in index.items():
            name = _name(raw_name)
            if not name.lower().endswith(SCRIPT_SUFFIXES):
                continue
            location = _entry(values, key)
            if location is None:
                continue
            offset, length = location
            if length <= 0 or length > MAX_ENTRY_BYTES:
                raise RPAError("Invalid entry size in %s: %s" %
                               (path.name, name))
            target = (destination / _relative(name)).resolve()
            if target != destination and destination not in target.parents:
                raise RPAError("Unsafe path in RPA: %s" % name)
            fh.seek(offset)
            data = fh.read(length)
            if len(data) != length:
                raise RPAError("Truncated entry in %s: %s" %
                               (path.name, name))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            extracted += 1
    if not extracted:
        raise RPAError("No scripts found in %s." % path.name)
    return extracted


def _check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise RPAError("Extraction cancelled.")


def extract_all(path, destination, cancel=None):
    path = Path(path)
    destination = Path(destination).resolve()
    index, key = _read_index(path)
    if not isinstance(index, dict) or not index:
        raise RPAError("Could not read RPA-3.0 archive: %s" % path.name)
    archive_size = path.stat().st_size
    entries = []
    for raw_name, values in index.items():
        name = _name(raw_name)
        location = _entry(values, key)
        if not name or location is None:
            continue
        offset, length = location
        if (offset < 0 or length < 0 or offset + length > archive_size or
                length > MAX_ALL_ENTRY_BYTES):
            raise RPAError("Invalid entry in %s: %s" % (path.name, name))
        target = (destination / _relative(name)).resolve()
        if target != destination and destination not in target.parents:
            raise RPAError("Unsafe path in RPA: %s" % name)
        entries.append((name, offset, length, target))
    if not entries:
        raise RPAError("No entries found in %s." % path.name)
    extracted = []
    with open(path, "rb") as source:
        for name, offset, length, target in entries:
            _check_cancel(cancel)
            target.parent.mkdir(parents=True, exist_ok=True)
            source.seek(offset)
            remaining = length
            with open(target, "wb") as output:
                while remaining:
                    _check_cancel(cancel)
                    block = source.read(min(COPY_CHUNK, remaining))
                    if not block:
                        raise RPAError("Truncated entry in %s: %s" %
                                       (path.name, name))
                    output.write(block)
                    remaining -= len(block)
            extracted.append(name)
    return extracted
