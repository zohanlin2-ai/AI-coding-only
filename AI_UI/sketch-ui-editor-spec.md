# Sketch-to-UI Editor Specification

## Purpose

Build a standalone HTML editor from a user-provided UI sketch. The editor must recreate the sketch as real, editable HTML components rather than using the sketch image as the final UI background.

The reference implementation is [remote-ui-editor.html](C:/Users/zohanlin/Documents/AI_UI/remote-ui-editor.html).

## Input Workflow

1. Inspect the supplied sketch and identify visible UI regions.
2. Create a component list. Every independently movable or resizable region becomes one component.
3. Assign each component an initial rectangle: `x`, `y`, `width`, and `height`, in canvas pixels.
4. Assign a semantic visual type and initial content.
5. Build the editor from those components. The sketch is a reference only, not the editable result.

## Required Editor Features

- Editable canvas width and height in pixels.
- Canvas resizing proportionally rescales every component.
- Components can be selected, dragged, resized from the lower-right handle, and edited numerically.
- Every component has:
  - `name`: editor-facing component name.
  - `type`: visual style or component category.
  - `content`: text, symbol, or icon character.
  - `contentScalePct`: independent content-size multiplier.
  - `contentOffsetX` and `contentOffsetY`: content position relative to its component.
  - `x`, `y`, `width`, and `height`.
- A component's content scales with its component, then uses `contentScalePct` for individual adjustment.
- A large outer D-pad nudges the selected component by 1px per action.
- A small nested D-pad nudges the selected component's content by 1px per action.
- Holding a D-pad button moves repeatedly after a short delay. Group one continuous hold into one Undo entry.
- Undo and Redo buttons plus keyboard shortcuts:
  - `Ctrl/Cmd + Z`: Undo.
  - `Ctrl/Cmd + Y` or `Ctrl/Cmd + Shift + Z`: Redo.
- Use English for the editor interface, labels, tooltips, and save dialog unless another language is explicitly requested.

## Boundary Rules

- A component must remain entirely inside the canvas.
- During drag, resize, numeric edits, canvas resizing, Undo, and Redo, clamp the component to the canvas.
- Content must remain inside its owning component.
- Content may touch the component edge but cannot move outside it.
- If a content-size multiplier would make text or an icon too large, use the maximum size that fits inside the component.

## Suggested Component Types

Use the smallest useful set of styles. Examples:

| Type | Typical use |
| --- | --- |
| `button` | Standard button or action area |
| `primary-button` | Main call-to-action |
| `secondary-button` | Lower-priority action |
| `display` | Screen or content panel |
| `label` | Small descriptive text |
| `icon-button` | Button whose content is an icon or symbol |
| `input` | Text, numeric, or search field |
| `card` | Grouped content container |
| `image` | Image placeholder or visual region |

Use semantic names such as `Save button`, `Search input`, or `Profile card`, not ambiguous names such as `Box 4`.

## Component Data Shape

```json
{
  "id": 1,
  "name": "Save button",
  "type": "primary-button",
  "content": "Save",
  "contentScalePct": 34,
  "contentOffsetX": 0,
  "contentOffsetY": 0,
  "x": 24,
  "y": 420,
  "width": 180,
  "height": 48
}
```

## Save Behavior

Provide one save action only: **Save PNG + JSON**.

1. Open an in-page dialog to enter a filename without an extension.
2. Ask for a destination folder once.
3. Save both files in that folder with the same base name:
   - `<filename>.png`: the current UI rendered without editor outlines or handles.
   - `<filename>.json`: canvas size and the full component list.
4. Use the browser File System Access API (`showDirectoryPicker`) when available. Explain that current Chrome or Edge is required if folder selection is unavailable.

## Deliverables for Each New Sketch

- A standalone English-named HTML file, for example `dashboard-ui-editor.html`.
- A JSON export produced by the editor at runtime.
- A PNG export produced by the editor at runtime.
- Optionally, a short design log explaining uncertain interpretations of the sketch.

## Quality Checklist

- Do not use the sketch image as the editable UI background.
- Verify each visible component has an editable HTML representation.
- Verify component and content movement cannot cross their respective boundaries.
- Verify content scales when its component changes size.
- Verify Undo/Redo covers drag, resize, fields, canvas resize, and D-pad movement.
- Verify PNG and JSON use one filename and one chosen destination folder.
- Run a JavaScript syntax check before delivery.

## Change Log

### 2026-07-21 — Overlapping component selection

- Do not raise a selected or hovered component above other components solely to show its editor outline.
- Smaller components that visually sit on top of a larger component must remain selectable with the mouse, even after the larger component has been selected.
- Keep selection labels and resize handles visible without intercepting pointer input intended for overlapping child or foreground components.
