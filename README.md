# Hashmal

Hashmal is an IDE for Bitcoin transaction scripts and a general cryptocurrency development toolbox. Its primary purpose is to make it easier to write, evaluate, and learn about transaction scripts.

Hashmal is intended for cryptocurrency developers and power users.

## Key Features

- Write scripts in human-readable form.
- Observe the stack as scripts are executed.
- See explanations of script operations as they are evaluated.
- Generate transaction scripts using templates.
- Deserialize and build transactions.
- Deserialize blocks.
- Communicate with full nodes or block explorers to retrieve blockchain data.
- Encode and decode addresses.

## Usage Tips

- See *Tools > Plugin Manager* in the menubar for details on what each tool does.
- You can manage tool layouts via *Tools > Settings* in the menubar.
- When typing opcodes, you can omit the `OP_` prefix for opcodes other than `OP_1, OP_2, ...OP_16`. For example, `DUP` and `OP_DUP` do the same thing.
- When editing scripts, put something in double quotation marks to ensure it's interpreted as text rather than hex data.
- You can quickly evaluate the script you're working on via *Script > Evaluate* in the menubar.

## Documentation

See the file `doc/usage.adoc` for basic instructions. See the [Hashmal wiki on Github](https://github.com/mazaclub/hashmal/wiki) for details.

The file `doc/plugins.adoc` has some information on the plugins system that Hashmal uses.


## License

GPLv3.
