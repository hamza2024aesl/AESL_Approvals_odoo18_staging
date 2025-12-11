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
})


publicWidget.registry.AppraisalGroupBy = publicWidget.Widget.extend({
    selector: '.appraisal-groupby-container',

    start() {
        const checkboxes = document.querySelectorAll('.group-by-checkbox-appraisal');
        const currentParams = new URLSearchParams(window.location.search);

        checkboxes.forEach(checkbox => {
            if (currentParams.get('group_by') === checkbox.value) {
                checkbox.checked = true;
            }

            checkbox.addEventListener('change', function () {
                const updatedParams = new URLSearchParams(window.location.search);

                if (this.checked) {
                    checkboxes.forEach(cb => {
                        if (cb !== this) cb.checked = false;
                    });
                    updatedParams.set('group_by', this.value);
                } else {
                    updatedParams.delete('group_by');
                }

                window.location.href = `${window.location.pathname}?${updatedParams.toString()}`;
            });
        });

        return this._super(...arguments);
    },
});


publicWidget.registry.AppraisalExpandButton = publicWidget.Widget.extend({
    selector: '.appraisal-expand-btn', // Apply to all group expand buttons
    events: {
        'click': '_onExpandAppraisalGroupClick',
    },

    _onExpandAppraisalGroupClick(ev) {
        ev.preventDefault(); // Prevent default action of the button

        const $btn = $(ev.currentTarget); // Get the button clicked
        const groupId = $btn.data('group-id'); // Get the group ID from the button's data attribute
        const $icon = $btn.find('.appraisal-expand-icon'); // Get the icon inside the button

        // Toggle the visibility of the group rows based on the group ID
        $(`.appraisal-group-row[data-group-id="${groupId}"]`).toggle();

        // Toggle between plus and minus icons
        $icon.toggleClass('fa-plus fa-minus');
    },
});


publicWidget.registry.AppraisalBulkApproval = publicWidget.Widget.extend({
    selector: '.appraisal-groupby-container',
    events: {
        'click #selectAllCheckbox': '_onSelectAllToggle',    // Select All Checkbox toggle
        'click #bulkApproveButton': '_onBulkApproveClick'    // Bulk Approve Button click
    },

    start() {
        this._super(...arguments);
    },

    // Handle the "Select All" checkbox toggle
    _onSelectAllToggle: function (ev) {
        const isChecked = ev.target.checked;
        const checkboxes = document.querySelectorAll('input[name="selected_appraisals"]');

        checkboxes.forEach(checkbox => {
            checkbox.checked = isChecked;
        });
    },

    // Handle the Bulk Approve Button click
    _onBulkApproveClick: function (ev) {
        const selectedAppraisals = [];
        const checkboxes = document.querySelectorAll('input[name="selected_appraisals"]:checked');

        checkboxes.forEach(checkbox => {
            selectedAppraisals.push(checkbox.getAttribute('data-id'));
        });

        if (selectedAppraisals.length > 0) {
            this._bulkApproveAppraisals(selectedAppraisals);
        } else {
            alert("Please select at least one appraisal to approve.");
        }
    },

    // Backend call to approve the selected appraisals
    _bulkApproveAppraisals: function (appraisalIds) {
        // Make an Ajax call to the backend to update the appraisals' state
        fetch('/my/appraisal/bulk/approve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                appraisal_ids: appraisalIds,
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Selected appraisals have been approved.");
                location.reload();
            } else {
                alert("Failed to approve selected appraisals.");
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("An error occurred while approving the appraisals.");
        });
    },
});


// publicWidget.registry.LocalStorageForm = publicWidget.Widget.extend({
//     selector: "#appraisal_detail",
//
//     events: {
//         "click .save-btn": "_saveToLocalStorage",
//     },
//
//     // Load saved data on page start
//     start: function () {
//         const saved = localStorage.getItem("appraisal_form_data");
//
//         if (saved) {
//             const formData = JSON.parse(saved);
//             this._applyValues(formData);
//         }
//
//         return this._super(...arguments);
//     },
//
//     // Save to localStorage
//     _saveToLocalStorage: function (ev) {
//         ev.preventDefault();
//
//         const formData = {};
//         this.$("input, textarea, select").each(function () {
//             formData[this.name] = $(this).val();
//         });
//
//         localStorage.setItem("appraisal_form_data", JSON.stringify(formData));
//
//         alert("Saved locally!");
//     },
//
//     // Fill values from localStorage
//     _applyValues: function (data) {
//         for (let key in data) {
//             this.$(`[name="${key}"]`).val(data[key]);
//         }
//     },
// });

