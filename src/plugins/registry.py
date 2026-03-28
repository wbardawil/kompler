# MIT License — DocuVault AI
"""Plugin loader and executor.

Layer: Integration (plugins)
Loads plugins from config, matches triggers against document metadata,
executes matching plugins in sequence after core enrichment.

Phase 2 deliverable.
"""
# TODO: Implement PluginRegistry class with:
# - load_plugins(plugins_dir) → discover and instantiate plugin classes
# - match(metadata: DocumentMetadata) → list of plugins whose triggers match
# - execute(metadata) → run all matching plugins, collect PluginResults
# - Trigger matching: "doc_type:supplier_certificate" matches metadata.doc_type == "supplier_certificate"
# - Emit plugin.executed event after each plugin runs
