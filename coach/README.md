# Coach

Coach is the root of the 408 learning architecture. It processes one real problem at a time and delivers the result into stable assets rather than leaving it in chat context or old-paper annotations.

The authority is [CONSTITUTION.md](CONSTITUTION.md).

## Runtime entry

- `today/MMDD.json`: T0's processed daily-question list.
- `current.md`: the single problem currently being handled.

Do not read the whole queue by default.

## Asset layers

- `knowledge/`: textbook-style 408 content, organized by subject and chapter.
- `analysis/<year>/qNN.md`: hard analysis of one original problem. The body starts by solving the problem directly and auditing options; it invokes knowledge rather than copying a course.
- `ability/`: personal problem-solving abilities proven by real-question evidence.
- `notes/<month>/MMDD.md`: downstream daily output, parallel to `src/<month>/`. Notes cite assets; they do not repeat their body.

## Pass

`pass` is the completed delivery of one problem. It means the problem is understood and its valuable result has a home in existing or newly created assets. It does not mean every related subject has been exhausted.

`revisit` and `pin` are reserved relationship markers. They are not directories, queues, or standalone notes.
