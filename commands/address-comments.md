The user wants to address comments on a plan file.

Determine which plan file to use:
- If arguments are provided (`$ARGUMENTS`), look for `plans/$ARGUMENTS.md` in the project root
- If no arguments, find the most recently modified `.md` file in the `plans/` directory

Then find all unresolved user comments — lines starting with `>` that do NOT contain `✅`.

For each unresolved comment:
1. Understand what the user is asking for, objecting to, or suggesting
2. Update the relevant section of the plan to address the feedback
3. Mark the comment resolved by changing `> comment` to `> ✅ comment`
4. Add a response line directly below: `> 📝 [what you changed or why you disagree]`

After all comments are addressed, run `open plans/<filename>.md` to refresh the file in the user's editor.

Then give a short summary of changes and say: "Review the updated plan. Add more `>` comments and save, then run `/address-comments <filename>` again — or say 'looks good' to proceed."
