/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";


publicWidget.registry.AppraisalsSubOrdinates = publicWidget.Widget.extend({
    selector: '.appraisals-subordinates-container',

    start() {
        const subordinateSwitch = document.getElementById('appraisals-sub-ordinates');
        const currentParams = new URLSearchParams(window.location.search);

        if (subordinateSwitch) {
            subordinateSwitch.checked = currentParams.get('subordinate') === '1';

            subordinateSwitch.addEventListener('change', function () {
                const updatedParams = new URLSearchParams(window.location.search);

                if (this.checked) {
                    updatedParams.set('subordinate', '1');
                } else {
                    updatedParams.delete('subordinate');
                }

                window.location.href = `${window.location.pathname}?${updatedParams.toString()}`;
            });
        }
        return this._super(...arguments);
    },
});