# Contributing

Thanks for helping. Keep changes small and tested.

1. Run `python scripts/check.py` to see that your machine has the tools.
2. Change one skill at a time. A skill's steps live in its `SKILL.md`; keep them true to what the
   scripts do.
3. Run the tests of the skill you changed:

   ```bash
   python skills/motion-video/scripts/test_motion.py
   python skills/motion-web-video/scripts/test_render.py
   python skills/motion-web-video/scripts/test_voice.py
   ```

   GitHub runs the same tests on every pull request.
4. If you change the plugin files, run `claude plugin validate . --strict`.

Rules for every change:
- **No secrets and no real data.** No keys, tokens, account numbers, bucket names, emails or
  customer names, in code, examples, screenshots or commits. Use made-up names (*Acme Board*,
  `example.com`, `example-training-media`).
- **Free by default.** A draft must never call a paid service. Paid steps ask first.
- **No new dependencies without a reason.** The web film needs no npm packages; keep it that way.
- Do not add Motion+ (paid) code.
