# Changelog

All notable changes to RainGod Comfy Studio will be documented in this file.

## [v15] - 2025-01-05

### Critical Fixes
- **Added z-index layering** - SVG connection layer (z-index: 1), nodes layer (z-index: 10), dragging node (z-index: 100)
  - Ensures SVG connections render under nodes properly
  - Prevents connection lines from blocking node interactions
  
- **VISIBLE connection flow lines** - SVG stroke visibility fixed
  - Connection lines are now properly visible on the canvas
  - Improved visual feedback for node connections
  
- **Explicit dragging state with Zustand** - Complete state management overhaul
  - Removed problematic `immer` middleware that was causing state update issues
  - Implemented clean dragging state: `isDragging`, `draggedNodeId`, `dragOffset`
  - Fixed node position updates to properly trigger re-renders
  
- **Null safety improvements** - Added comprehensive null/undefined checks
  - Protected against runtime errors from missing node references
  - Improved error handling throughout the application

### Features
- **Node deletion functionality** - Users can now delete nodes from the workflow
- **Connection management** - Proper connection creation and visualization
- **Draggable nodes** - Full drag-and-drop support with mouse and touch
- **Real-time workflow execution** - Process audio through connected nodes
- **Memory-optimized architecture** - Uses Web Workers for heavy processing

### Technical Improvements
- Removed `immer` middleware dependency
- Streamlined state updates for better performance
- Fixed pointer event blocking issues
- Improved SVG rendering and layering
- Enhanced null safety across all components

### Known Limitations
- WebSim iframe environment may limit some drag interactions
- Full source code editing requires WebSim platform access

## [v4] - 2025-01-04

### Initial Release
- Basic node-based workflow interface
- Prompt, Synthesis, Effect, and Output nodes
- Initial drag-and-drop implementation
- Web Worker integration for audio processing

---

## Development Notes

### Version History Context
This project was developed iteratively through WebSim with multiple bug fix iterations:
- v4: Initial implementation with basic features
- v5-v14: Various attempts to fix dragging and connection issues
- v15: **STABLE** - All critical bugs resolved

### WebSim Deployment
Live version: https://websim.com/@GenesisArchitect/raingod-comfy-studio

The live WebSim deployment contains the complete, fully-functional v15 codebase including:
- index.html
- main.jsx
- components/Node.jsx
- components/WorkflowGraph.jsx  
- state/WorkflowStore.js
- audio/ProcessorWorker.js

### Inspiration
Built with inspiration from ComfyUI's node-based workflow system:
- GitHub: https://github.com/comfyanonymous/ComfyUI
- Studied DragAndScale.ts for drag implementation patterns

### Repository Purpose
This GitHub repository serves as:
1. Documentation hub for the project
2. Version history tracking
3. Public access point with redirect to live deployment
4. Code reference for v15 implementation details
