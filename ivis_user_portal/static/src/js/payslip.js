/* @odoo-module */

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.PayslipGroupBy = publicWidget.Widget.extend({
    selector: '.payslip-groupby-container',

    start() {
        this._super(...arguments);

        const checkboxes = this.el.querySelectorAll('.group-by-checkbox-payslip');
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
                    window.location.href = `/my/payslips?group_by=${this.value}`;
                } else {
                    window.location.href = '/my/payslips';
                }
            });
        });

        return this;
    },
});

publicWidget.registry.PayslipExpandButton = publicWidget.Widget.extend({
    selector: '.payslip-expand-btn',
    events: {
        'click': '_onExpandPayslipGroupClick',
    },

    _onExpandPayslipGroupClick(ev) {
        ev.preventDefault();

        const $btn = $(ev.currentTarget);
        const groupId = $btn.data('group-id');
        const $icon = $btn.find('.payslip-expand-icon');

        $(`.payslip-group-row[data-group-id="${groupId}"]`).toggle();
        $icon.toggleClass('fa-plus fa-minus');
    },
});