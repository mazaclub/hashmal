# Hashmal

Hashmal is an IDE for Bitcoin transaction scripts. Its purpose is to make it easier to write, evaluate, and learn about transaction scripts.

Hashmal is intended for cryptocurrency developers and power users.

Use at own risk!

## Key Features

- Write scripts in human-readable form.
- Observe the stack as scripts are executed.
- See explanations of script operations as they are evaluated.


## Usage Tips

- See *Help > Tool Info* in the menubar for details on what each tool does.
- You can manage tool layouts via *Tools > Settings* in the menubar.
- When typing opcodes, you can omit the `OP_` prefix for opcodes other than `OP_1, OP_2, ...OP_16`. For example, `DUP` and `OP_DUP` do the same thing.
- When editing scripts, put something in double quotation marks to ensure it's interpreted as text rather than hex data.
- You can quickly evaluate the script you're working on via *Script > Evaluate* in the menubar.


## To-Do

- When evaluating scripts, `OP_CHECKSIG`/`OP_CHECKSIGVERIFY` cannot be used because they require a transaction in addition to the script.
