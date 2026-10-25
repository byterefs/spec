# Decision records

Each open question in [BRIEF.md](../BRIEF.md) section 6 is closed by a
numbered record here, not by an edit to the specification alone.

- File name: `NNNN-short-title.md`, numbered in order, never reused.
- Status: `proposed`, `accepted`, `superseded by NNNN`, or `rejected`.
- A record enters `main` with status `proposed`, through a pull request
  that adds it. Merging that pull request records the proposal; it does not
  accept it.
- Acceptance is a separate, later pull request that changes the status to
  `accepted` (or `rejected`) and adds the date and a link to the
  discussion. That pull request is the record's review step.
- The specification text changes only once a record is accepted, in the
  acceptance pull request or after it.
- A later record may supersede an earlier one; the earlier one is kept.

Template: [0000-template.md](0000-template.md).
