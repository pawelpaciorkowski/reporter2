# TODO: w tym teście zdefiniować reguły dla atrybutów elementów dialogów i sprawdzać. Może być na podstawie dialogu
#  z Techniczne/TestInterfejsu - co wystąpi tam może wystąpić, inne elementy nie


def test_dialogs_should_return_their_description(plugin_with_dialog):
    dialog = plugin_with_dialog.LAUNCH_DIALOG
    definition = dialog.get_definition()
    assert isinstance(definition, list)
    assert len(definition) == 3
    assert isinstance(definition[0], str)
    assert isinstance(definition[1], list)
    assert definition[1] == ['Dialog', 'Panel', 'Container']
    assert isinstance(definition[2], dict)


def test_dialog_elements_hierarchy():
    pass


def test_dialog_elements_attributes():
    pass


def test_dialog_elements_params_loading():
    pass


def test_plugin_with_dialog_should_have_start_report_or_be_limited_to_admin(plugin_with_dialog):
    if not hasattr(plugin_with_dialog, 'start_report'):
        assert plugin_with_dialog.REQUIRE_ROLE == 'ADMIN'
