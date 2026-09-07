/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    BooleanToggleField,
    booleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";


class PrelogIncludeCheckbox extends BooleanToggleField {
    static template = "web.BooleanField";

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onChange(newValue) {
        this.state.value = newValue;
        await this.orm.write(
            this.props.record.resModel,
            [this.props.record.resId],
            { [this.props.name]: newValue }
        );
        await this.props.record.load();
    }
}

registry.category("fields").add("prelog_include_checkbox", {
    ...booleanToggleField,
    component: PrelogIncludeCheckbox,
});


class PrelogGeneratorFormController extends FormController {
    setup() {
        super.setup();
        this.display.controlPanel = false;
    }
}

registry.category("views").add("prelog_generator_form", {
    ...formView,
    Controller: PrelogGeneratorFormController,
});
