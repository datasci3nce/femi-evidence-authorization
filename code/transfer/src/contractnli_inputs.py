#!/usr/bin/env python3
"""Use an official ContractNLI ZIP or extracted JSON with the transfer builder.
No downloads, no model calls. Only the requested JSON member is extracted.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import zipfile


def is_contractnli_json(path):
    try:
        with pathlib.Path(path).open(encoding="utf-8") as f:
            o = json.load(f)
        return (isinstance(o, dict) and isinstance(o.get("documents"), list)
                and len(o["documents"]) > 0 and isinstance(o.get("labels"), dict)
                and len(o["labels"]) > 0
                and isinstance(o["documents"][0], dict)
                and "annotation_sets" in o["documents"][0])
    except (OSError, json.JSONDecodeError, UnicodeError, ValueError):
        return False


def prepare(source, output):
    source = pathlib.Path(source).expanduser().resolve()
    output = pathlib.Path(output).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"ContractNLI input does not exist: {source}")
    if output == source:
        if not is_contractnli_json(output):
            raise ValueError("Input does not match the official ContractNLI JSON format")
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            files = [x for x in archive.infolist() if not x.is_dir()
                     and pathlib.PurePosixPath(x.filename).name in ("test.json", "dev.json")]
            if not files:
                raise ValueError("Archive has no test.json or dev.json. Upload the official contract-nli.zip")
            files.sort(key=lambda x: (pathlib.PurePosixPath(x.filename).name != "test.json", len(x.filename), x.filename))
            selected = files[0]
            # Extract a single member by stream, never extract arbitrary paths.
            if selected.file_size > 200_000_000:
                raise ValueError("ContractNLI JSON exceeds safety limit")
            with archive.open(selected) as input_file, output.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
            print(f"Selected ZIP member: {selected.filename}")
    elif source.suffix.lower() == ".json":
        shutil.copyfile(source, output)
    else:
        raise ValueError("Upload the official ContractNLI ZIP or a test.json/dev.json extracted from it")
    if not is_contractnli_json(output):
        output.unlink(missing_ok=True)
        raise ValueError("The selected JSON is not an annotated ContractNLI document split")
    raw = output.read_bytes()
    data = json.loads(raw)
    print(f"ContractNLI ready: {output} | {len(data['documents'])} documents | SHA256 {hashlib.sha256(raw).hexdigest()}")
    return output


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="Official ZIP or test.json/dev.json")
    ap.add_argument("--output", required=True, help="Destination test.json")
    args = ap.parse_args()
    prepare(args.input, args.output)
