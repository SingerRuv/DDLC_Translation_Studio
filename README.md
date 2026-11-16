# DDLC Translation Studio

Independent translation tool for precompiled DDLC/Ren'Py mods.

## Status

Phase 5 is complete for the translation build workflow. The workspace,
project database, mod detection, external-tool configuration, script indexing,
validation, CSV/CLI workflow, Tkinter editor, script rewriting, Ren'Py
compilation, translated build generation, and Windows packaging are
implemented. The release workflow is next.

## GUI

```powershell
python app.py
python app.py "C:\path\to\project"
```

## CLI

```powershell
python app.py detect "C:\path\to\mod"
python app.py tools
python app.py prepare "C:\path\to\mod" "C:\path\to\project"
python app.py index "C:\path\to\project"
python app.py apply "C:\path\to\project"
python app.py build "C:\path\to\project" "C:\path\to\empty-output"
python app.py strings "C:\path\to\project"
python app.py set "C:\path\to\project" 1 "Translated text"
python app.py validate "C:\path\to\project"
python app.py export "C:\path\to\project" "strings.csv"
python app.py import "C:\path\to\project" "strings.csv"
```

`prepare` requires an RPA extractor and an `.rpyc` decompiler. Their paths and
arguments can be configured in `~/.ddlc_translation_studio/settings.json`, or
overridden with `--rpa-tool` and `--rpyc-tool`.

## Windows Build

```powershell
powershell -File build\build_windows.ps1
```

The executable is written to `dist/windows/DDLCTranslationStudio.exe`.

## Scope

The first version targets standard precompiled DDLC mods with Ren'Py 6, 7, or 8.

The workflow will be:

1. Select a precompiled mod.
2. Detect its Ren'Py version and folder structure.
3. Copy the mod into a workspace.
4. Extract its RPA archives with an external tool.
5. Decompile `.rpyc` files with an external tool.
6. Index translatable dialogue and menu strings.
7. Edit translations manually.
8. Validate variables, tags, placeholders, quotes, and line breaks.
9. Rewrite the `.rpy` sources in the workspace.
10. Compile them with the Ren'Py SDK.
11. Produce a complete translated copy of the mod.
12. Keep the original mod and its RPA archives untouched.

## Dependencies

The application will use external, user-installed tools:

- an RPA extractor;
- `unrpyc` or an equivalent `.rpyc` decompiler;
- the Ren'Py SDK version matching the target mod.

The tool will detect and validate configured paths. It will not bundle or
redistribute those external tools in the first version.

## Phase 0 result

Ren'Py checks files on disk before archive files. The relevant `loadable_core`
function attempts `transfn(name)` before iterating through RPA indexes.

This behavior was verified in:

- Ren'Py 6, from the DDLC 1.1.1 base (`renpy/loader.py`);
- Ren'Py 7, from a prebuilt mod (`renpy/loader.py`);
- Ren'Py 8.5.3 SDK (`renpy/loader.py`).

Therefore, a loose `.rpyc` at the same relative path should take precedence
over the same file inside an RPA archive. This is the basis for keeping the
original RPA intact and placing translated `.rpyc` files in `game/`.

A full runtime fixture test is still required before implementing the build
step.

## Planned structure

```text
DDLCTranslationStudio/
??? app.py
??? ddlc_translator/
?   ??? config.py
?   ??? modinfo.py
?   ??? project.py
?   ??? tools.py
?   ??? workspace.py
?   ??? indexer.py
?   ??? validate.py
?   ??? rewrite.py
?   ??? build.py
?   ??? gui.py
??? tests/
??? build/
??? README.md
??? LICENSE
```

## Non-goals for the first version

- MAS or MAS submods.
- AI translation.
- Automatic submod merging.
- Sprite pack merging.
- Replacing the original RPA archives.
- Integration with DDLC Mod Manager.
- Universal compatibility with every Ren'Py mod.

## License

MIT. See `LICENSE`.
