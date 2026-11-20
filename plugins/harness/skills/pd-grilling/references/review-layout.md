# Review layout (no wall of text)

The `AskUserQuestion` dialog shows `question` as one run-on paragraph. It cannot render a table. Text
printed just before the dialog is replaced by a one-line summary, so do not rely on it. The `preview`
field of an option is the place for the evidence: it shows as a boxed block beside the options.

1. Put the evidence in the `preview` of the option that accepts it (the "Recommended" or "go" option).
   One line per item: `#31  errors  400 bad_request; 404 not_found; HOST=127.0.0.1`. Keep each line
   at most 55 characters, because the box wraps there. Put the exact names, numbers and paths the
   owner must check in the line. Use the same short labels (`#31`) in the dialog.
2. `question` names the decision and the count only, for example "Accept the 5 recommended answers?".
3. `preview` works only on a single-select question. Give the other options no preview.
4. A "confirm all" question is allowed only when every item is in the preview. Offer "I will adjust"
   so the owner can name the items to change by label.
5. A `question` of more than 40 words, or more than 2 sentences, is a defect. Move the rest to the
   preview.
