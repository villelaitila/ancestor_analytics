import copy
import re
import sys
from typing import Dict, Set, List

from sgraph import SElement

from except_utils import conditional_raise

yb_pat = re.compile(r'[A-ZÅÄÖa-zåäö()] ([0-9][0-9]?\.[0-9][0-9]?\.)?([12][0-9][0-9][0-9])')


def dash_after(left_part, match):
    end = match.end()
    if len(left_part) > end:
        x = left_part[end]
        return x in {'-', '–'}
    return False



def get_cousins(elem, second_level_ancestors_dict, second_level_descendants_dict):
    cousins = []
    for ancestor in second_level_ancestors_dict[elem]:
        for cousin in second_level_descendants_dict[ancestor]:
            cousins.append(cousin)
    if elem in cousins:
        cousins.remove(elem)
    return cousins


def get_second_level_descendants(elem):
    for first_level_assoc in elem.incoming:
        for second_level_assoc in first_level_assoc.fromElement.incoming:
            yield second_level_assoc.fromElement


def get_second_level_ancestors(elem):
    for first_level_assoc in elem.outgoing:
        for second_level_assoc in first_level_assoc.fromElement.outgoing:
            yield second_level_assoc.toElement


def find_kids_with_cousins(graph):
    second_level_descendants_dict: Dict[SElement, Set[SElement]] = {}
    second_level_ancestors_dict: Dict[SElement, Set[SElement]] = {}

    for elem in graph.rootNode.children:
        second_level_descendants_dict[elem] = set(get_second_level_descendants(elem))
    for elem in graph.rootNode.children:
        second_level_ancestors_dict[elem] = set(get_second_level_ancestors(elem))

    for elem in graph.rootNode.children:
        children = []
        for child_assoc in elem.incoming:
            children.append(child_assoc.fromElement)

        if children:
            for cousin in get_cousins(elem, second_level_ancestors_dict,
                                      second_level_descendants_dict):
                common = []
                # find out commin children with the cousin
                for cousin_child_assoc in cousin.incoming:
                    if cousin_child_assoc.fromElement in children:
                        common.append(cousin_child_assoc.fromElement)
                if common:
                    print(f'Common children with cousins {elem.name} {cousin.name}:')
                for common_child in common:
                    print(f'    {common_child.name}')


# Find cousin marriages


def find_parent_is_a_sibling_and_other_stuff(graph):
    issues = []
    for elem in graph.rootNode.children:
        parents = []
        for parent_assoc in elem.outgoing:
            parents.append(parent_assoc.toElement)

        for parent_assoc in elem.outgoing:
            for pparent_assoc in parent_assoc.toElement.outgoing:
                if pparent_assoc.toElement in parents:
                    issues.append((elem, parents))

    if issues:
        print('Found issues with parent == parents.parent')
        for issue in issues:
            print(issue)


def verify_basic_natural_requirements(graph):
    # Verify
    for x in graph.rootNode.children:
        if len(x.outgoing) > 2:
            raise Exception(
                f'Invalid combination, three parents: {x.name}\n  {[x.toElement.name for x in x.outgoing]}')

    # verify_counts
    for elem in graph.rootNode.children:
        if len(elem.outgoing) > 2:
            raise Exception(f'Element cannot have more than 2 parents here: {elem.name}'
                            f'  Parents: {" ".join(elem.outgoing)}')

    # verify structure
    for elem in graph.rootNode.children:
        if elem.children:
            raise Exception(f'Element {elem.name} has children: {elem.children[0].name}')


def verify_subgraphs(graph):
    def verify_n_connections(node, n):
        found = []
        stack = [node]
        handled = set()
        while stack:
            elem = stack.pop(0)
            if elem in handled:
                continue
            handled.add(elem)
            for i in elem.incoming:
                found.append(i.fromElement)
                stack.append(i.toElement)
            for i in elem.outgoing:
                found.append(i.toElement)
                stack.append(i.toElement)
            if len(found) > n:
                return

    for node in graph.rootNode.children:
        verify_n_connections(node, 5)


def verify_common_parents_with_children_counts(graph):
    for node in graph.rootNode.children:
        if node.incoming:
            children = [x.fromElement for x in node.incoming]
            parents_ea_list = [child.outgoing for child in children]
            parents = set([item.toElement for sublist in parents_ea_list for item in sublist])
            parents.remove(node)
            if len(parents) > 3:
                raise Exception('Suspiciously high number of common parents, must be an error\n')
            elif len(parents) > 2:
                sys.stderr.write('Suspiciously high number of common parents: \n')
                parents_names = set([item.toElement.name for sublist in parents_ea_list for item in sublist])
                sys.stderr.write(str(parents_names) + '\n')
            elif len(parents) > 1:
                print(f'{node.name} has {len(children)} children who have {len(parents)} other '
                      f'parents: ')
                for parent in parents:
                    print(f'   {parent.name}  kids: {len(parent.incoming)}')


def find_cousin_marriages(graph, level):
    # this --> parent --> grandparent --> grandgrandparent has multiple matches

    def traverse_1(original_element, element, paths_per_grand_grand_grand_parents, path, level):
        path.append(element)
        if level - 1 > 0:
            for parent in element.outgoing:
                traverse_1(original_element, parent.toElement, paths_per_grand_grand_grand_parents,
                           path, level - 1)
        else:
            paths_per_grand_grand_grand_parents.setdefault(element, []).append(list(path))

        path.pop(len(path) - 1)

    for original_element in graph.rootNode.children:
        paths_per_grand_grand_grand_parents: Dict[SElement, List[List[SElement]]] = {}
        path = []
        for parent_ea in original_element.outgoing:
            path.append(parent_ea.toElement)
            for grandparent_ea in parent_ea.toElement.outgoing:
                path.append(grandparent_ea.toElement)
                for grandgrandparent_ea in grandparent_ea.toElement.outgoing:
                    traverse_1(original_element, grandgrandparent_ea.toElement,
                               paths_per_grand_grand_grand_parents, path, level)
                path.pop(len(path) - 1)
            path.pop(len(path) - 1)

        if paths_per_grand_grand_grand_parents:
            found = False
            for k, paths in paths_per_grand_grand_grand_parents.items():
                if len(paths) > 1:
                    first_elements = set()
                    for path in paths:
                        first_elements.add(path[0])
                    if len(first_elements) == 1:
                        continue

                    found = True
                    break

            if found:
                name_cleaned = original_element.name.split('\n')[0]
                print(
                    f'Parents of {name_cleaned.split()[0]} are {level}. cousins due to common ancestor.')
                print(f'  Child: ' + name_cleaned)
                print(f'   Parents:')
                for parent_ea in original_element.outgoing:
                    print(f'        {parent_ea.toElement.name}')

        for k, paths in paths_per_grand_grand_grand_parents.items():
            if len(paths) > 1:
                # Ignore those cases where
                first_elements = set()
                for path in paths:
                    first_elements.add(path[0])
                if len(first_elements) == 1:
                    continue

                ancestor_name = k.name.replace('\n', ' ').strip()
                print(f'              Common ancestor: {ancestor_name}')

                if level > 0:
                    print('              Paths:')
                    for path_to_same_anc in paths:
                        print('                   ' + ' => '.join(
                            map(lambda x: x.name.split('\n')[0], path_to_same_anc)))

    return


def find_getting_child_with_parent(graph, known_problem_cases):
    for node in graph.rootNode.children:
        children = [x.fromElement for x in node.incoming]
        parents = [x.toElement for x in node.outgoing]
        for child in children:
            for parent_of_child_ea in child.outgoing:
                if parent_of_child_ea.toElement in parents:
                    accepted = False
                    for known in known_problem_cases:
                        if known in node.name or known in parent_of_child_ea.toElement.name:
                            accepted = True
                            break
                    if not accepted:
                        raise Exception(f'Child with a parent: {node.name} '
                                        f'parent={parent_of_child_ea.toElement.name}')


def find_if_parents_parent_is_parent(graph, known_problem_cases):
    for node in graph.rootNode.children:
        parents = [x.toElement for x in node.outgoing]
        for ea_parent in node.outgoing:
            for ea_parents_parent in ea_parent.toElement.outgoing:
                accepted = False
                for known in known_problem_cases:
                    if known in node.name or known in ea_parents_parent.toElement.name:
                        accepted = True
                        break
                if accepted:
                    continue

                if ea_parents_parent.toElement in parents:
                    raise Exception(f'Parent\'s parent {ea_parents_parent.toElement.name} is parent for'
                                    f' {node.name}.')
                """
                TODO!!!!!  Anna Enygeus bint Joseph is parent for Caradog ap Bran
                for ea_parents_parents_parent in ea_parents_parent.toElement.outgoing:
                    if ea_parents_parents_parent.toElement in parents:
                        raise Exception(f'Parent\'s parent\'s parent '
                                        f'{ea_parents_parents_parent.toElement.name} is parent '
                                        f'for {node.name}.')
                """


def find_if_name_startswith_someones_elses_name(graph):
    issues = []
    for node in graph.rootNode.children:
        for node2 in graph.rootNode.children:
            if node != node2 and node.name.startswith(node2.name):
                sys.stderr.write(
                    'Name starts with someone else\'s name: ' + node2.name + '  --- ' + node.name + '\n\n')
                issues.append((node2.name, node.name))
    return issues


def detect_duplicate_persons_based_on_name_and_year(graph):
    # See if there are suspiciously similar persons
    identifier_to_persons = {}
    person_name_and_year_of_birth_pattern = re.compile('^([A-ZÅÄÖa-zåäö ]+-?[12][0-9][0-9][0-9])')
    for person in graph.rootNode.children:
        identifier = person_name_and_year_of_birth_pattern.search(person.name)
        if identifier:
            identifier_to_persons.setdefault(identifier.group(1), []).append(person)

    def abbrev_deps(person):
        s = ''
        for ea in person.incoming:
            s += ea.fromElement.name[0]
        for ea in person.outgoing:
            s += ea.fromElement.name[0]
        return s

    for k, v in identifier_to_persons.items():
        if len(v) > 1:
            print('\nSuspiciously similar person identifiers')
            for person in v:
                print(f'    <{person.name}>  {abbrev_deps(person)} ')


def verify_unique_names(graph):
    names = set()
    for element in graph.rootNode.children:
        if element.name in names:
            raise Exception('Non-unique names: ' + element.name)
        names.add(element.name)


def look_for_very_similar_persons(graph, exceptions_allowed):
    pat = re.compile(
        '([12][0-9][0-9][0-9]+) [A-Za-zÅÄÖåäö, ]+ K. ([12][0-9][0-9][0-9]) [A-Za-zÅÄÖåäö, ]+')
    for elem1 in graph.rootNode.children:
        name1 = elem1.name
        m1 = None
        if ' K.' in name1:
            m1 = pat.search(name1)
            if m1:
                for elem2 in graph.rootNode.children:
                    if elem1 != elem2:
                        name2 = elem2.name
                        if ' K. ' in name2 and m1.group(1) in name2:
                            m2 = pat.search(name2)
                            if m2:
                                if m1.group(1) == m2.group(1) and m1.group(2) == m2.group(2):
                                    if name1[0:8] == name2[0:8] and not name1 in exceptions_allowed:
                                        msg = 'Same lifespan:\n    "' + name1 + '"\n    "' + name2 + '"'
                                        raise Exception(msg)


def find_closest_linked_ancestor_without_necessary_details(graph, check_level=8):
    # Show closest linked that have
    #  - no parents
    #  - no birth year
    #  - no place of birth
    without_two_parents = [x for x in graph.rootNode.children if len(x.outgoing) < 2]

    def collect_descendants(person, current):
        out = []
        for ea in person.incoming:
            current_2 = copy.copy(current)
            current_2.append(person)
            persons = collect_descendants(ea.fromElement, current_2)
            out.extend(persons)

        if out:
            return out

        if not person.incoming:
            return [current + [person]]

    def show_mystery(person):
        descendants = collect_descendants(person, [])
        matches = False
        for d in descendants:
            if len(d) < check_level:
                matches = True
                break

        if not matches:
            return

        d_list = set()
        d = None
        for d in descendants:
            d_list.add(d[-1].name)
        print(person.name.replace('\n', '\n  '))
        if re.search('[12][0-9][0-9][0-9]', d[1].name):
            print('     ' + descendants[0][1].name.replace('\n', ' '))
        else:
            print('     ' + descendants[0][1].name.replace('\n', ' '))
            print('         ' + descendants[0][2].name.replace('\n', ' '))
        print('                     .... ' + str(d_list))
        print('')

    recent_year_pat = re.compile(' 1[89][0-9][0-9]')
    other_year_pat = re.compile(' 1[76543210][0-9][0-9]')
    for elem in without_two_parents:
        if recent_year_pat.search(elem.name):
            pass  # todo print(elem.name)
        elif other_year_pat.search(elem.name):
            pass
        else:
            show_mystery(elem)


num_dash_num_pat = re.compile(r'[0-9]-[0-9]')

year_digits_pat = re.compile(r'-?[1-2][0-9][0-9][0-9]')


def check_naming_conventions(graph):
    verify_description_duplication(graph)

    for node in graph.rootNode.children:
        lines = node.name.split('\n')
        if '"' in lines[0]:
            raise Exception(
                'First row should not contain double quotes ("):    ' + node.name.split('\n')[0])
        if len(lines[0].split('(')) > 2:
            raise Exception('First row should not contain several parenthesis:  ' + node.name)
        if ' K. ' not in lines[0]:
            # Basic number check
            if ' 1' in lines[0]:
                m = year_digits_pat.search(lines[0])
                if m:
                    m2 = year_digits_pat.search(lines[0][m.end():])
                    if m2 and m2.start() > 3:
                        raise Exception(
                            'Two years without K.:                           ' + lines[0])
            if lines[0].count('-') > 1:
                raise Exception('negative numbers? without K.:                         ' + lines[0])
        else:
            # K. in lines[0]
            right_part = lines[0].split(' K. ')[1]
            if '  ' in right_part:
                raise Exception(f'Double space in K. part: "{right_part}"\n{lines[0]}')
        if len(lines) > 1 and lines[1].startswith('K. '):
            raise Exception('Node second line starts with K.  :' + node.name)
        m = num_dash_num_pat.search(lines[0])
        if m:
            pos_a = lines[0].find(' arviolta')
            if pos_a > m.start():
                pos_a = -1
            if pos_a == -1:
                raise Exception('Year range needs keyword arviolta, name=           ' + lines[0])
        if 'description' in node.attrs and '**' not in node.name:
            conditional_raise('Not using ** for description: ' + node.name)
        if 'description' not in node.attrs and '**' in node.name:
            conditional_raise('using ** without description: ' + node.name)


def verify_description_duplication(graph):
    desc_map = {}
    for node in graph.rootNode.children:
        if 'description' in node.attrs:
            desc_map.setdefault(node.attrs.get('description'), []).append(node)
    for k, v in desc_map.items():
        if len(v) > 1:
            print('Duplicated descriptions found for: ')
            for vv in v:
                print(vv.name)

            print('Desc:')
            print('   ' + k)
            raise Exception('Stopping on duplicated descs.')


def verify_graph(graph, verbose=False, known_problem_cases=None):
    verify_unique_names(graph)
    verify_basic_natural_requirements(graph)
    find_parent_is_a_sibling_and_other_stuff(graph)
    detect_duplicate_persons_based_on_name_and_year(graph)
    find_getting_child_with_parent(graph, known_problem_cases)
    find_if_parents_parent_is_parent(graph, known_problem_cases)
    name_issues = find_if_name_startswith_someones_elses_name(graph)
    find_kids_with_cousins(graph)

    [x.attrs.pop('year_of_birth') for x in graph.rootNode.children if 'year_of_birth' in x.attrs]

    # TODO !!!! verify_birth_years(graph)
    verify_subgraphs(graph)
    verify_common_parents_with_children_counts(graph)

    verbose = False  # TODO !!!!!

    if verbose:
        find_cousin_marriages(graph, 1)
        print('Cousins at 2 level\n============================================0\n')
        find_cousin_marriages(graph, 2)
        # find_cousin_marriages(graph, 3)
        # find_cousin_marriages(graph, 4)

    # TODO !!!!!!!!! avoid now
    # look_for_very_similar_persons(graph, exceptions_allowed_for_similar_persons)
    # TODO find_closest_linked_ancestor_without_necessary_details(graph)
    # Todo check also missing details
    # todo here check genders also

    # TODO !!!!!!!!! avoid now
    #  check_naming_conventions(graph)
    return name_issues

# Check all the children who have two parents to see if the rest of the children in the same
# family don't have 2 parents. Hmm. Not maybe useful info since it is fairly possible.
