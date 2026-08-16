# V76K2 Source-Criticism Notes

The app should privilege structural markings over benchmark-style verdicts.

## Correct issue from the screenshot critique

A multimodal example can show a person in an image and a text claim, but that does not mean the pictured person is affiliated with the claim.  The missing question is:

> Is the person/material in the image actually affiliated with the evaluated claim?

V76K2 adds an explicit affiliation-gap review lane for that issue.

## Rejected product logic

Do not use FEVER, AVeriTeC, or MICE-style benchmark logic as the app's classification baseline.  These systems are verdict/evaluation frameworks, not a HOME repository source-criticism model.

## Accepted product logic

Use deterministic source structure:

- material type: video/audio/image/text chain
- source address
- sustainable marking
- source chain basis
- bias notes
- affiliation with the claim
- final human-review source role

The extractor layer may gather fields, but it does not decide source role.
