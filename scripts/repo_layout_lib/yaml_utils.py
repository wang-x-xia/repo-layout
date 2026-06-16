import yaml
from typing import Any


class Dumper(yaml.Dumper):
    """
    Custom YAML dumper with metadata key sorting and multiline text support.
    """
    def represent_mapping(self, tag: str, mapping: dict, flow_style: Any = None) -> yaml.Node:
        """
        Override represent_mapping to sort metadata keys first.

        Args:
            tag: YAML tag
            mapping: Dictionary to represent
            flow_style: Flow style for mapping

        Returns:
            YAML mapping node
        """
        value = []
        # Separate keys into metadata keys (starting with :) and regular keys
        meta_keys = [k for k in mapping.keys() if k.startswith(':')]
        regular_keys = [k for k in mapping.keys() if not k.startswith(':')]

        # Sort both groups
        meta_keys.sort()
        regular_keys.sort()

        # Process metadata keys first, then regular keys
        for item_key in meta_keys + regular_keys:
            node_item = self.represent_data(item_key)
            node_value = self.represent_data(mapping[item_key])
            value.append((node_item, node_value))

        if flow_style is None:
            flow_style = self.default_flow_style

        return yaml.MappingNode(tag, value, flow_style=flow_style)


def represent_multiline_str(dumper: Dumper, data: str) -> yaml.Node:
    """
    Custom string representer for multiline text support.

    Args:
        dumper: Dumper instance
        data: String to represent

    Returns:
        YAML scalar node
    """
    if '\n' in data:
        # Use literal block scalar for multiline strings
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


# Register custom string representer
yaml.add_representer(str, represent_multiline_str, Dumper)


def dump(data: Any, file=None, **kwargs) -> str:
    """
    Dump data to YAML with metadata sorting and multiline text support.

    Args:
        data: Data to dump
        file: Optional file object to write to (default: None, returns string)
        **kwargs: Additional arguments for yaml.dump

    Returns:
        YAML string if file is None, otherwise None
    """
    # Set default kwargs
    default_kwargs = {
        'default_flow_style': False,
        'sort_keys': False,
        'allow_unicode': True,
        'Dumper': Dumper
    }
    default_kwargs.update(kwargs)

    return yaml.dump(data, file, **default_kwargs)
