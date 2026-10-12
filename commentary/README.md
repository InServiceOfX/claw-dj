# Commentary

Writing that claw-dj shows as pop-ups over the stream and in mix videos, next
to the agent's music facts. One folder per author, named for them:

```
commentary/
  ernest-yeung/          ← Ernest's writing (marked "EY")
    author.json          ← {"name": "...", "initials": "EY"}
    _template.md         ← how to write a piece (never shown)
    some-essay.md        ← your pieces (Markdown)
    distilled.md         ← optional: your own "in brief" summaries as "- " bullets
  <another-author>/      ← anyone else, with their own initials
```

Everything here is public. Each pop-up from an author's folder carries that
author's initials. The agent's facts (`brain/popup_facts.json`) carry no mark.

See `docs/POPUPS.md` for running the overlay and `_template.md` for writing.
