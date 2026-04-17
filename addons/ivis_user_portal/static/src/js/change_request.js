/* @odoo-module */

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ChangeRequest = publicWidget.Widget.extend({
    selector: '.monitor-datetime',
    events: {
        'input': '_onInput',
    },

    async _onInput(event) {
        event.preventDefault();
        $('#request_submit_id').prop('disabled', true);

        const currentInput = event.target;
        const currentInputId = event.target.id;

        let ID = null

        if ($(currentInput).hasClass('new_check_in_id')) {
            ID = currentInputId.slice(15);
        }
        else if ($(currentInput).hasClass('new_check_out_id')) {
            ID = currentInputId.slice(16);
        }

        const dateFrom = $("#new_check_in_id" + ID).val()
        const dateTo = $("#new_check_out_id" + ID).val()

        if (dateFrom && dateTo && (dateFrom <= dateTo)) {
            $('#att_duration_err_id' + ID).hide()
            $('#request_submit_id' + ID).prop('disabled', false);
        }
        else if (dateFrom && dateTo && (dateFrom > dateTo)) {
            $('#att_duration_err_id' + ID).show()
            $('#request_submit_id' + ID).prop('disabled', true);
        }
    },
})

