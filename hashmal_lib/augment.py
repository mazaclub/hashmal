from collections import namedtuple

AugmentStep = namedtuple('AugmentStep', ('augmenter_plugin_name', 'result'))
"""Model of a completed augmentation."""

class Augmentable(object):
    """Model of an augmentation requester.

    Attributes:
        requester (str): Class that requests augmentation.
        hook_name (str): Augmentation hook name.
        initial_data: Data to pass to augmenters.
        callback: Function that is called with augmentation results.

    """
    def __init__(self, requester, hook_name, initial_data=None, callback=None, undo_callback=None):
        self.requester = requester
        self.hook_name = hook_name
        self.initial_data = initial_data
        self.callback = callback
        self.undo_callback = undo_callback
        self.steps = []

    def add_step(self, augmenter_plugin_name, data):
        step = AugmentStep(augmenter_plugin_name, data)
        self.steps.append(step)

    def get_result(self, plugin_name):
        """Get the augmentation result for plugin_name."""
        for step in self.steps:
            if step.augmenter_plugin_name == plugin_name:
                return step.result

    def __str__(self):
        return '%s.%s' % (self.requester, self.hook_name)

class Augmentation(object):
    """Model of an augmentation.

    Attributes:
        - augmenter_plugin: Plugin instance that has the augmenter.
        - augmentable: Augmentable object.
        - has_run: Whether the augmentation has been done.
        - is_enabled: Whether the augmentation can be done.
    """
    def __init__(self, augmenter_plugin, augmentable):
        self.augmenter_plugin = augmenter_plugin
        self.augmentable = augmentable

        self.has_run = False
        self.is_enabled = True

    def __str__(self):
        return '%s.%s' % (self.augmenter_plugin.name, self.augmentable.hook_name)

    def do_callback(self, data):
        """Call the requester's callback.

        Also records the result in the augmentable's steps list.
        """
        # Record step in augmentable.
        self.augmentable.add_step(self.augmenter_plugin.name, data)

        if self.augmentable.callback:
            self.augmentable.callback(data)

    def undo_callback(self, data):
        """Call the requester's undo callback."""
        if self.augmentable.undo_callback:
            self.augmentable.undo_callback(data)

    def get_function(self):
        """Get the augmenter function."""
        return self.augmenter_plugin.get_augmenter(self.augmentable.hook_name)

    def run_function(self):
        """Run the augmenter function."""
        func = self.get_function()
        return func(self.augmentable.initial_data)

    def does_augment_requester(self):
        """Get whether this augmentation would augment the requester that requests augmentation."""
        return self.augmentable.requester == self.augmenter_plugin.ui.__class__.__name__

    def can_run(self):
        """Get whether the augmentation should be run."""
        if self.has_run or not self.is_enabled or self.does_augment_requester():
            return False
        return True

class Augmentations(object):
    """Handler for Augmentation instances."""
    def __init__(self):
        # {requester.hook_name: [AugmentStep(), ...], ...}
        self.augmentables = {}
        self.augmentations = []

    def get_augmentation(self, plugin, hook_name, requester, data=None, callback=None, undo_callback=None):
        """Get or create an augmentation."""
        augmentable = self.augmentables.get('%s.%s' % (requester, hook_name))
        # If no augmentable is known, create it.
        if not augmentable:
            augmentable = Augmentable(requester, hook_name, data, callback, undo_callback)
            self.augmentables[str(augmentable)] = augmentable

        # If the augmentation exists, return it.
        augmentation = self.get(plugin.name, hook_name)
        if augmentation:
            return augmentation

        # Otherwise, create the augmentation.
        augmentation = Augmentation(plugin, augmentable)
        self.augmentations.append(augmentation)
        return augmentation

    def get(self, augmenter_plugin_name, hook_name):
        """Get the Augmentation for augmenter_plugin_name.hook_name."""
        for i in self.augmentations:
            if i.augmenter_plugin.name == augmenter_plugin_name and i.augmentable.hook_name == hook_name:
                return i
        return None

    def get_completed_augmentations(self, augmenter_plugin_name):
        return filter(lambda i: i.has_run, filter(lambda j: j.augmenter_plugin.name == augmenter_plugin_name, self.augmentations))

    def get_disabled_augmentations(self, augmenter_plugin_name):
        return filter(lambda i: i.is_enabled == False, filter(lambda j: j.augmenter_plugin.name == augmenter_plugin_name, self.augmentations))

    def do_augment(self, augmentation):
        """Call an augmenter and record its result."""
        if not augmentation.can_run():
            return

        data = augmentation.run_function()

        augmentation.do_callback(data)
        augmentation.has_run = True

    def undo_augment(self, augmentation):
        """Undo an Augmentation."""
        if not augmentation.has_run:
            return

        data = augmentation.augmentable.get_result(augmentation.augmenter_plugin.name)
        augmentation.undo_callback(data)
        augmentation.has_run = False
