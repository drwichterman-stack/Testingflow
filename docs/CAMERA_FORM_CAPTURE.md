# Camera form capture

With **Capture form** you hold a completed paper form up to the Mac's camera. ClinAssess reads the marked response boxes and fills in the data-entry form. You check and correct every response before you save.

It is available for the free paper forms: SDQ, SNAP-IV, ASRS v1.1, WSR-II, CATS, WFIRS-P, and WFIRS-S. It is not offered for licensed instruments; their scores come from the publisher's software.

## How it works

1. Open the assessment and choose the form and informant. Then click **Capture form**.
2. The camera preview opens. Hold the page flat, filling most of the picture, in front of a darker background. Keep it still and click **Snap** (or press Space). For forms with more than one page, click **Snap next page**.
3. ClinAssess finds the page edges and straightens the photo.
4. **First time for each form:** select a block on the right (for example "Items 1-25"). Click **Outline** and drag a box from the top-left corner of the first item's first response box to the bottom-right corner of the last item's last response box. Then drag the pink corners to fit. The outline covers the response boxes only, not the item text.
5. **Next time:** the saved outlines are placed on the new photo automatically. Check that they line up, and drag corners if needed.
6. Check the dots on the photo:
   - **Green:** one clear mark was read.
   - **Amber:** a faint or unclear mark. Check it.
   - **Red:** no mark was found, or there is more than one mark.
7. Click **Apply to form**. The responses are filled in. Every doubtful item has a flag under it (⚠ Check, ⚠ No mark, ⚠ 2+ marks). WSR-II safety items (suicide items and self-injurious behaviour) are **always** flagged, even when they were read clearly.
8. Compare **every** response with the paper form, not only the flagged ones. Click a flag once its item is correct, or click the correct response. If you try to save while flags remain, ClinAssess asks you to confirm.

### Blocks, splits, and column order

- A **block** is a run of consecutive items that share the same response options, printed as evenly spaced rows. By default each section of the form is one block.
- Use **Split block...** when a block continues in another column or on the next page, or when a heading sits between its items. Then outline each part separately. Splits are saved with the outlines.
- Response columns are read left to right in the order the app lists them under the table (for example "Not True | Somewhat True | Certainly True"). If a printed form runs from highest to lowest, tick **Columns run from highest to lowest response**.

## Getting good reads

| Do | Avoid |
|---|---|
| Ask respondents to mark with a dark pen: an X, a check, or a filled box | Pencil, tiny ticks, or marks outside the box |
| Fill the camera picture with the page | A small page far from the camera |
| Hold the page flat and still, against a darker background | A white wall behind a white page (edges cannot be found) |
| Use even room light | Strong shadows or glare across the boxes |
| Outline tightly around the response boxes | Including headings or item text in the outline |

If the page edges are not found, the whole photo is used. Saved outlines may then be out of place, so fit them by hand.

## Privacy and security

- **Photos stay in memory.** They are never written to disk, never stored in the database, and are discarded when the capture window closes.
- **Nothing leaves the Mac.** Reading is done in ClinAssess with numpy and Pillow. There is no cloud OCR service and no network connection.
- **Outlines** (page-relative coordinates and item numbers, no PHI) are kept in the encrypted database.
- **Audit trail:** `FORM_CAPTURE` records the instrument, variant, number of pages, and counts of read, check, blank, and multiple items (no responses). `ASSESSMENT_CREATE` or `ASSESSMENT_UPDATE` records `camera_capture` and the number of flags left unchecked at save. `SCAN_LAYOUT_SAVE` records when outlines are saved.
- **Camera permission:** macOS asks the first time. The built app declares the reason (`NSCameraUsageDescription`) and, when signed, the camera entitlement. When running from source, macOS asks for permission for Terminal.

## How reading works (for reviewers)

`clinassess/omr.py` holds the reading engine. It uses no Qt code, so it can be unit tested.

1. **Page:** the largest bright region of the photo is taken as the page. Its corners are found along the diagonals, and the page is straightened to 1275 pixels wide.
2. **Block:** the outlined quadrilateral is straightened into a grid of cells, which corrects tilt and perspective. An adaptive threshold separates ink from paper under uneven light.
3. **Layout:** printed table lines give exact cell edges when present. Otherwise row and column centres come from the printed boxes. Detected positions must lie within 35% of a row or column spacing of even spacing. If they cannot be found, even spacing is assumed, the block shows a warning, and **no item in it counts as a clear read**.
4. **Marks:** each cell gets a score from ink coverage (large marks such as circles and fills) plus peak local ink density (small, dense marks such as checks). The score of an unmarked cell in the same column (the printed box or digit) is subtracted. The noise level is estimated from the unmarked cells. Each item is then **read** (one strong mark), **check** (weak mark, or a second weaker mark), **blank**, or **multiple**.
5. The engine never reads item text. No instrument content is needed or stored.

### Tested accuracy (synthetic forms only)

The test suite draws synthetic forms with four layouts (boxes, circles, printed digits, ruled tables) and four mark styles (X, check, filled, circled). It then simulates camera photos with tilt, perspective, blur, noise, uneven light, and JPEG compression. It also includes 1080p laptop-camera-sized snaps read with saved outlines.

- In every tuning and test run, no wrong response was ever reported as a clear read. Doubtful items are always flagged.
- About 86% to 96% of marked items were read clearly. Most of the rest were right but flagged. Tiny ticks are flagged about half the time, which is why dark X or filled marks are recommended.

**Synthetic results are not a clinical validation.** Printed forms, pens, cameras, and lighting vary. Validate on real forms before relying on the feature (see COMPLIANCE_REVIEW.md, Part E).
