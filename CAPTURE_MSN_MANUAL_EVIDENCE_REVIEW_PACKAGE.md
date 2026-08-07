# MSN manual capture Evidence Review package

This section closes the next local implementation bridge for MSN manual captures.

The package builder turns an explicit MSN manual Evidence Queue report into a deterministic Evidence Review package. The flow is still local/operator-controlled, but it is no longer observation-only:

1. an approved action kit creates explicit operator artifact slots;
2. article/comment artifacts are extracted into a Total Export package;
3. the Total Export package is queued for evidence review;
4. this section builds a review package with review actions, asset roles, hashes, and status.

Safety boundaries remain in force: the package does not run live HTTP, browser automation, archive submission, media download, credential access, WARC/WACZ creation, or folder scans. Inputs are explicit files supplied by the operator, and outputs keep safe filenames and hashes rather than full local paths.
