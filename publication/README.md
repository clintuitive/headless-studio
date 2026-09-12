# Publication source

This is the maintained intermediate manuscript and static website source.
`build_epub.py` generates the EPUB from all twenty chapter/appendix files.
`build.py` builds HTML locally; it never deploys or clears a remote directory.
Install `requirements.txt` first. The local studio's `Blog/` is a working
mirror; synchronize edits here before publishing a repository revision.

Audio downloads are hosted on clintjohnson.cloud and excluded from Git.
A code-only build does not include those recordings. Put release media in
`downloads/` to make a complete deployment bundle. Do not deploy a partial
build over the live listening page. The EPUB is generated into that same
folder before the HTML build.
