# DDLC Translation Studio

Desktop translation and build tool for DDLC/Ren'Py source projects.

The current application is a PySide6/Qt rewrite. It replaces the old Tkinter
version and is focused on one workflow: prepare a source project, translate
its visible text, and compile a playable build using a DDLC base for assets.

## Requirements

- Windows 10/11.
- Python 3.12+ for development.
- PySide6 6.12.0.
- Ren'Py SDK 6, 7, or 8 matching the source project.
- A complete DDLC base folder, used only for `fonts.rpa`, `images.rpa`, and
  `audio.rpa`.
- A complete Ren'Py project (`game/`, `lib/`, `renpy/`, and launcher), or a
  DDLC overlay (`game/scripts.rpa` + `game/mod_assets.rpa`).
- Scripts may be `.rpy` sources or compiled `.rpyc`/RPA content.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app from source:

```powershell
python app.py
```

## Workflow

1. Click **New project**.
2. Select the complete DDLC base folder.
3. Select a complete Ren'Py project or a DDLC overlay.
4. The app creates a project in:
   ```text
   ~/DDLC Translation Studio Projects/<mod>
   ```
5. The workspace copies only `game/` from the source project.
6. Every RPA in that `game/` folder is extracted and deleted from the
   workspace.
7. Missing `.rpy` sources are decompiled with the bundled `unrpyc`.
8. Only visible text is indexed: dialogue, narration, menu choices, character
   names, and screen text. Asset paths, colors, style data, and Python
   internals are excluded.
9. Translate the strings in the inline table.
10. Use validation, CSV import/export, search, and status filters as needed.
11. Click **Build mod** to create a playable build.

## Build behavior

The final build is written to:

```text
~/DDLC Mods/<mod> - Translated
```

If that folder exists, a numeric suffix is added.

The build:

- uses the runtime and launcher from the source project, or from the DDLC
  base when the source is an overlay;
- for overlays, also copies `game/python-packages/` from the base;
- replaces the output `game/` with the translated workspace `game/`;
- copies `fonts.rpa`, `images.rpa`, and `audio.rpa` from the DDLC base;
- removes mod RPA archives and `scripts.rpa`;
- compiles scripts with the SDK matching the source project's Ren'Py version;
- keeps all compiled `.rpyc` files;
- keeps `.rpy` only for scripts that contain translations;
- leaves the source project and base folder untouched.

The three base asset RPAs are intentionally retained: DDLC mods check for
them at startup. Loose translated/mod assets take precedence over those
archives.

For runtime builds, base and source versions do not need to match because
the source provides the runtime. Overlay builds use the base runtime, so the
base and SDK version must match the overlay's Ren'Py version (Ren'Py 6 for
Doki Doki: Within).

## Script indexing

The indexer is intentionally conservative. It targets visible strings and
ignores:

- RPA and asset paths;
- color values;
- `show`, `scene`, `play`, `voice`, `image`, and style statements;
- Python blocks and `$` lines;
- screen definitions that contain no visible text.

If a source expression is not detected, it can be added to the indexer rules
without changing the rest of the project.

## SDK settings

Open **Settings** and configure the paths for Ren'Py 6, 7, and 8, or let the
app auto-detect them from common locations. The editor works without an SDK;
the build requires the exact version detected in the source project.

## Project layout

```text
~/DDLC Translation Studio Projects/<mod>/
??? project.sqlite3
??? workspace/
    ??? game/
    ??? original/
```

`workspace/game` is the translated working tree. `workspace/original` is the
snapshot used to apply translations idempotently.

## Development

Run tests:

```powershell
python -m unittest discover -s tests -v
```

Build the Windows executable:

```powershell
powershell -File build/build_windows.ps1
```

The executable is written to `dist/windows/DDLCTranslationStudio.exe`.

## Scope and limitations

- RPA-3.0 only.
- Source projects may be complete Ren'Py projects or DDLC overlays.
- The source project may be a `.rpy` source tree or a compiled runtime whose
  `game/` contains script RPA files; compiled scripts are extracted and
  decompiled into the workspace.
- The source project must contain all game scripts needed to run.
- Windows is the supported packaging target.
- The build is designed for DDLC mods; other Ren'Py projects may need extra
  compatibility work.
- Existing translated builds are not overwritten automatically.

## Third-party components

`unrpyc` is bundled under the MIT license. See
`ddlc_studio/vendor/unrpyc/LICENSE` and `THIRD_PARTY_NOTICES.md`.

## License

MIT. See `LICENSE`.
