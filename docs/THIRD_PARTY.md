# Stockpile — Third-Party Software & Open-Source Credits

Stockpile presents a unified first-party product experience. The technologies below are documented here rather than exposed as primary product branding.

## Clip generation

**OpenShorts**  
Repository: https://github.com/mutonby/openshorts  
License: MIT

Stockpile integrates with the project's long-form clip-generation capabilities through an adapter/API boundary. Provider-specific details are intentionally kept out of normal Stockpile UI copy.

The upstream repository includes a separate licensing exception for content under its `cloud/` directory. Stockpile does not assume that the cloud directory is covered by the repository's MIT license.

Upstream copyright notice:

> OpenShorts  
> Copyright (c) 2024 OpenShorts

The applicable MIT license is available in the upstream repository's `LICENSE` file.

## Caption motion references

**motion-anything**  
Repository: https://github.com/nexu-io/motion-anything  
License: Apache License 2.0

Stockpile uses a native caption-motion abstraction and references motion/recipe concepts from this project. The current Stockpile integration is intentionally decoupled from the upstream application rather than exposing its name in the product UI.

Upstream copyright notice:

> Copyright 2026 nexu.io

The applicable Apache License 2.0 is available in the upstream repository's `LICENSE` file.

## Editable timeline integration

**OpenReel Video**  
Repository: https://github.com/Augani/openreel-video  
License: MIT

Stockpile integrates with the editable browser timeline through a dedicated adapter and project representation. The end-user feature is branded simply as **Timeline Editor** in the Stockpile UI.

Stockpile-specific integration code remains behind internal service boundaries so the public product surface is stable and can evolve independently of the upstream editor.

The exact upstream fork/version used for a deployment should be recorded when distributing a bundled editor build.

## Attribution policy

Third-party names and repositories belong in engineering documentation, license notices, and credits—not in normal workflow labels unless disclosure is technically necessary.

Stockpile does not claim authorship of third-party software. License obligations are evaluated against the exact upstream components actually copied, modified, bundled, or called at distribution time.

Last reviewed: 2026-09-29
