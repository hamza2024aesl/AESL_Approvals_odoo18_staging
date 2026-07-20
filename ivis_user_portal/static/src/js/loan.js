/* @odoo-module */

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.LoanConditions = publicWidget.Widget.extend({
    selector: '.loan-input, .loan-groupby-container',
    events: {
        'input': '_onInput',
    },

    async _onInput(event) {
        event.preventDefault();
        $('#submit_loan_id').prop('disabled', true);

        const amount = $('#req_amt_id').val();

        if (amount > 0) {
            $('#submit_loan_id').prop('disabled', false);
        }
    },

    start() {
        this._super(...arguments);

        const checkboxes = this.el.querySelectorAll('.group-by-checkbox-loan');
        const currentParams = new URLSearchParams(window.location.search);

        checkboxes.forEach(checkbox => {
            if (currentParams.get('group_by') === checkbox.value) {
                checkbox.checked = true;
            }

            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    checkboxes.forEach(cb => {
                        if (cb !== this) {
                            cb.checked = false;
                        }
                    });
                    window.location.href = `/my/loans?group_by=${this.value}`;
                } else {
                    window.location.href = '/my/loans';
                }
            });
        });

        return this;
    },
})

publicWidget.registry.LoanExpandButton = publicWidget.Widget.extend({
    selector: '.loan-expand-btn',
    events: {
        'click': '_onExpandLoanGroupClick',
    },

    _onExpandLoanGroupClick(ev) {
        ev.preventDefault();

        const $btn = $(ev.currentTarget);
        const groupId = $btn.data('group-id');
        const $icon = $btn.find('.loan-expand-icon');

        $(`.loan-group-row[data-group-id="${groupId}"]`).toggle();
        $icon.toggleClass('fa-plus fa-minus');
    },
});