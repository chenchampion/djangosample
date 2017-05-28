from django import template

from oscar.core.compat import assignment_tag
from oscar.core.loading import get_model

register = template.Library()
Partner = get_model('partner', 'Partner')

assignment_tag = assignment_tag(register)


@assignment_tag(name="partner_tree")
def get_annotated_list(depth=None, parent=None):
    """
    Gets an annotated list from a tree branch.

    Borrows heavily from treebeard's get_annotated_list
    """
    # 'depth' is the backwards-compatible name for the template tag,
    # 'max_depth' is the better variable name.
    max_depth = depth

    annotated_partners = []

    start_depth, prev_depth = (None, None)
    if parent:
        partners = parent.get_descendants()
        if max_depth is not None:
            max_depth += parent.get_depth()
    else:
        partners = Partner.objects.all()

    info = {}
    for node in partners:
        node_depth = 0
        if start_depth is None:
            start_depth = node_depth
        if max_depth is not None and node_depth > max_depth:
            continue

        # Update previous node's info
        info['has_children'] = prev_depth is None or node_depth > prev_depth
        if prev_depth is not None and node_depth < prev_depth:
            info['num_to_close'] = list(range(0, prev_depth - node_depth))

        info = {'num_to_close': [],
                'level': node_depth - start_depth}
        annotated_partners.append((node, info,))
        prev_depth = node_depth

    if prev_depth is not None:
        # close last leaf
        info['num_to_close'] = list(range(0, prev_depth - start_depth))
        info['has_children'] = prev_depth > prev_depth

    return annotated_partners