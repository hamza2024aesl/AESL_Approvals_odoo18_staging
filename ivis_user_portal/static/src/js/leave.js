/* @odoo-module */

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.LeaveExpandButton = publicWidget.Widget.extend({
    selector: '.leave-expand-btn',
    events: {
        'click': '_onExpandLeaveGroupClick',
    },

    _onExpandLeaveGroupClick(ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const groupId = $btn.data('group-id');
        const $icon = $btn.find('.leave-expand-icon');

        $(`.leave-group-row[data-group-id="${groupId}"]`).toggle();
        $icon.toggleClass('fa-plus fa-minus');
    },
});

publicWidget.registry.ExpandButton = publicWidget.Widget.extend({
    selector: '.row-expand-btn',
    events: {
        'click': '_onExpandLeaveLinesClick',
    },

    _onExpandLeaveLinesClick(ev) {
        ev.preventDefault();

        const $btn = $(ev.currentTarget);
        const leaveId = $btn.data('leave-id');
        const $detailsRow = $(`#details-row-${leaveId}`);
        const $icon = $btn.find('.row-expand-icon');
        if ($detailsRow.length) {
            $detailsRow.toggle();
            $icon.toggleClass('fa-plus fa-minus');
        }
    },
});

publicWidget.registry.DateAndDuration = publicWidget.Widget.extend({
    selector: '.compute-duration, .description-input, .leave-groupby-container, #half_day, #time_off_type, #date_from_period_id',
    events: {
        'input': '_onInput',
    },

    init() {
        $('#already_booked_id').hide();
        $('#date_from_id').val(new Date().toISOString().split('T')[0]);
        $('#date_to_id').val(new Date().toISOString().split('T')[0]);
        this._checkHalfDayValidity();
        this._checkHalfDayDuration();
    },

    async _onInput(event) {
        if (
            event.currentTarget.classList.contains('compute-duration')
            || event.currentTarget.classList.contains('description-input')
            || event.currentTarget.id === 'date_from_period_id'
        ) {
            await this.leaveSubmition(event);
        }
        if (event.currentTarget.id === 'half_day') {
            await this._checkHalfDayDuration();
        }
        if (event.currentTarget.id === 'time_off_type') {
            await this._checkHalfDayValidity();
        }
    },

    start() {
        this._super(...arguments);

        const subordinateSwitch = document.getElementById('leave-sub-ordinates');
        const checkboxes = document.querySelectorAll('.group-by-checkbox-leaves');
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

        const checkboxesManage = document.querySelectorAll('.group-by-checkbox-leaves-manage');
        const currentParamsManage = new URLSearchParams(window.location.search);

        checkboxesManage.forEach(checkbox => {
            if (currentParamsManage.get('group_by') === checkbox.value) {
                checkbox.checked = true;
            }

            checkbox.addEventListener('change', function () {
                if (this.checked) {
                    checkboxesManage.forEach(cb => {
                        if (cb !== this) cb.checked = false;
                    });
                    window.location.href = `/my/leaves/manage?group_by=${this.value}`;
                } else {
                    window.location.href = `/my/leaves/manage`;
                }
            });
        });

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

        return this;
    },

    async _checkHalfDayValidity() {
        const timeoffType = $('#time_off_type').val();
        await rpc('/my/leaves/check_halfday', {
            holiday_status_id: timeoffType || '',
        }).then((result) => {
            $('#half_day').prop('checked', false);
            $('#half_day').prop('disabled', !result);
            this._checkHalfDayDuration();
        });
    },

    async _checkHalfDayDuration() {
        const halfDay = $('#half_day').is(':checked');
        $('#duration_id').val(halfDay ? 0.5 : 0);
        $('#date_to_id').val(halfDay ? "" : new Date().toISOString().split('T')[0]);
        $('#date_to_id').parent().css('display', halfDay ? 'none' : 'block');
        $('#date_from_period_id').parent().css('display', halfDay ? 'block' : 'none');
        $('#submit_leave_id').prop('disabled', !halfDay);
        if (halfDay) {
            this.leaveSubmition();
        }
    },

    async leaveSubmition() {
        $('#submit_leave_id').prop('disabled', true);

        const dateFrom = $('#date_from_id').val();
        const dateTo = $('#date_to_id').val();
        const halfDay = $('#half_day').is(':checked');
        const period = $('#date_from_period_id').val();

        if (
            (dateFrom && dateTo && (dateFrom <= dateTo))
            || (dateFrom && halfDay)
        ) {
            $('#duration_error_id').hide()
            const newDateFrom = new Date(dateFrom);
            const newDateTo = new Date(dateTo);

            const isWeekend = date => date.getDay() === 0 || date.getDay() === 6;
            let differenceDays = 0;
            for (let date = newDateFrom; date <= newDateTo; date.setDate(date.getDate() + 1)) {
                if (!isWeekend(date)) {
                    differenceDays++;
                }
            }

            if (!halfDay) {
                $('#duration_id').val(differenceDays)
            }

            const result = await rpc('/my/leaves/check_duration', {
                date_from: dateFrom,
                date_to: dateTo,
                half_day: halfDay,
                period: period,
            })

            if (result == false) {
                $('#already_booked_id').show();
                $('#submit_leave_id').prop('disabled', true);
                return;
            }
            if (result && halfDay) {
                $('#already_booked_id').hide();
                $('#submit_leave_id').prop('disabled', false);
            }
            else if (result && differenceDays != 0) {
                $('#already_booked_id').hide();
                $('#submit_leave_id').prop('disabled', false);
            }
            else if (differenceDays == 0) {
                $('#already_booked_id').hide();
                $('#submit_leave_id').prop('disabled', true);
            }
            else {
                $('#submit_leave_id').prop('disabled', true);
            }
        }
        else if (dateFrom && dateTo && (dateFrom > dateTo)) {
            $('#duration_id').val(0)
            $('#duration_error_id').show()
            $('#submit_leave_id').prop('disabled', true);
        }
    },
})

publicWidget.registry.LeaveListViewPortal = publicWidget.Widget.extend({
    selector: '.cancel-leave, .approve-leave',
    events: {
        click: '_onClickCancelLeave',
    },

    async _onClickCancelLeave(event) {
        event.preventDefault();
        const leaveId = event.currentTarget.id;

        if (event.currentTarget.classList.contains('cancel-leave')) {
            event.currentTarget.classList.remove('btn-close');
            event.currentTarget.classList.add('btn-close-load');
            await rpc('/leave/cancel', {
                leave_id: leaveId,
            }).then(() => {
                window.location.reload();
            });
        }
        if (event.currentTarget.classList.contains('approve-leave')) {
            event.currentTarget.classList.remove('btn-approve');
            event.currentTarget.classList.add('btn-approve-load');
            await rpc('/leave/approve', {
                leave_id: leaveId,
            }).then(() => {
                window.location.reload();
            });
        }
    }
})


// publicWidget.registry.HalfDay = publicWidget.Widget.extend({
//     selector: '#half_day, #time_off_type',
//     events: {
//         'input': '_halfDayHandling',
//     },

//     async _halfDayHandling(event) {
//         if (event.currentTarget.id === 'half_day') {
//             const halfDay = $('#half_day').is(':checked');
//             // Disable Duration To
//             $('#duration_id').val(halfDay ? 0.5 : 0);
//             $('#date_to_id').val(halfDay ? "" : "");
//             $('#date_to_id').prop('disabled', halfDay);
//             $('#submit_leave_id').prop('disabled', !halfDay);


//         }
//         if (event.currentTarget.id === 'time_off_type') {
//             const timeoffType = $('#time_off_type').val();
//             await rpc('/my/leaves/check_halfday', {
//                 holiday_status_id: timeoffType,
//             }).then((result) => {
//                 $('#half_day').prop('disabled', !result);
//             });
//         }
//     },
// })