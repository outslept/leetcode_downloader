# LeetCode Submission Collect

Minimal tool to archive your LeetCode submissions. Login once, fetch fast, store clean.

## Usage

- Run: python lcus_submission.py
- First run opens Chrome. Log in and complete verification, then return to the terminal and press Enter.

Example output:

```
Linked to user: alice
Setting up browser…
Browser ready [0.9s]
Checking session…
Session detected [0.4s]
Syncing session…
Session ready
Fetching submissions…
page 1: +20 (total 20)
page 2: +20 (total 40)
Fetched 183 submissions [5.2s]
Writing files…
Saved 72 accepted solutions to lcus_alice/Accepted [0.8s]
Closing browser…
Done [7.1s]
```

## Data layout

```
lcus_<username>/
  Accepted/
    <slug>.<ext>
  <slug>/
    <timestamp>.json
```

## Config

- `LEETCODE_URL`: switch to https://leetcode.cn if needed
- `BATCH_SIZE`: number of submissions per request
- `LANG_EXTENSIONS`: map LeetCode language to file extensions
- Chrome profile dir: `~/.leetcode_chrome`

## License

MIT