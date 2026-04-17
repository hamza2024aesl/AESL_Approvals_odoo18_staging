/* @odoo-module */

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

const LEAVE_ACTION_SELECTORS = '#btn-approve-selected, .approve-leave, .cancel-leave, #btn_refuse_leave';
let leaveActionsLocked = false;

function setLeaveActionsDisabled(disabled) {
    const $buttons = $(LEAVE_ACTION_SELECTORS);
    $buttons.prop('disabled', disabled);
    if (disabled) {
        $buttons.addClass('disabled');
    } else {
        $buttons.removeClass('disabled');
    }
}

function lockLeaveActions() {
    if (leaveActionsLocked) {
        return false;  // already locked, ignore new actions
    }
    leaveActionsLocked = true;
    setLeaveActionsDisabled(true);
    return true;
}

function unlockLeaveActions() {
    leaveActionsLocked = false;
    setLeaveActionsDisabled(false);
}

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
         'change': '_onInput',
    },

    start() {
        this._super(...arguments);

        $('#already_booked_id').hide();
        $('#duration_error_id').hide();

        const today = new Date().toISOString().split('T')[0];
        if (!$('#date_from_id').val()) {
            $('#date_from_id').val(today);
        }
        if (!$('#date_to_id').val()) {
            $('#date_to_id').val(today);
        }

        Promise.resolve(this._checkHalfDayDuration()).then(() => this.leaveSubmition());

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

        const subordinateSwitch = document.getElementById('leave-sub-ordinates');
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

    async _onInput(event) {
        if (
            event.currentTarget.classList.contains('compute-duration')
            || event.currentTarget.classList.contains('description-input')
            || event.currentTarget.id === 'date_from_period_id'
        ) {
            await this.leaveSubmition();
        }

        if (event.currentTarget.id === 'half_day') {
            await this._checkHalfDayDuration();
            await this.leaveSubmition();
        }

        if (event.currentTarget.id === 'time_off_type') {
            await this._checkHalfDayValidity();
            await this.leaveSubmition();
        }
    },

    async _checkHalfDayValidity() {
        const timeoffType = $('#time_off_type').val();

        const result = await rpc('/my/leaves/check_halfday', {
            holiday_status_id: timeoffType || '',
        });

        $('#half_day').prop('checked', false);

        await this._checkHalfDayDuration();
    },

    async _checkHalfDayDuration() {
        const halfDay = $('#half_day').is(':checked');

        $('#duration_id').val(halfDay ? 0.5 : 0);

        if (halfDay) {
            $('#date_to_id').val('');
            $('#date_to_id').parent().css('display', 'none');
            $('#date_from_period_id').parent().css('display', 'block');
        } else {
            if (!$('#date_to_id').val()) {
                $('#date_to_id').val(new Date().toISOString().split('T')[0]);
            }
            $('#date_to_id').parent().css('display', 'block');
            $('#date_from_period_id').parent().css('display', 'none');
        }
    },

    async leaveSubmition() {
        const dateFrom = $('#date_from_id').val();
        const dateTo = $('#date_to_id').val();
        const halfDay = $('#half_day').is(':checked');
        const period = $('#date_from_period_id').val();

        const effectiveDateTo = halfDay ? dateFrom : dateTo;

        if (
            (dateFrom && effectiveDateTo && (dateFrom <= effectiveDateTo))
        ) {
            $('#duration_error_id').hide();

            const newDateFrom = new Date(dateFrom);
            const newDateTo = new Date(effectiveDateTo);

            const isWeekend = d => d.getDay() === 0 || d.getDay() === 6;

            let differenceDays = 0;
            for (let d = new Date(newDateFrom); d <= newDateTo; d.setDate(d.getDate() + 1)) {
                if (!isWeekend(d)) differenceDays++;
            }

            if (halfDay) {
                $('#duration_id').val(0.5);
            } else {
                $('#duration_id').val(differenceDays);
            }

            const result = await rpc('/my/leaves/check_duration', {
                date_from: dateFrom,
                date_to: effectiveDateTo,
                half_day: halfDay,
                period: period,
            });

            if (result === false) {
                $('#already_booked_id').show();
                $('#submit_leave_id').prop('disabled', true);
                return;
            }

            $('#already_booked_id').hide();

            if (halfDay) {
                $('#submit_leave_id').prop('disabled', false);
                return;
            }

            if (differenceDays !== 0) {
                $('#submit_leave_id').prop('disabled', false);
            } else {
                $('#submit_leave_id').prop('disabled', true);
            }
        } else if (dateFrom && dateTo && (dateFrom > dateTo) && !halfDay) {
            $('#duration_id').val(0);
            $('#duration_error_id').show();
            $('#submit_leave_id').prop('disabled', true);
        } else {
            $('#submit_leave_id').prop('disabled', true);
        }
    },
});

publicWidget.registry.LeaveListViewPortal = publicWidget.Widget.extend({
    selector: '.cancel-leave, .approve-leave',
    events: {
        click: '_onClickCancelLeave',
    },

    async _onClickCancelLeave(event) {
        event.preventDefault();
        const $btn = $(event.currentTarget);

        if ($btn.hasClass('approve-leave')) {
            if (!lockLeaveActions()) {
                return;
            }

            const leaveId = $btn.attr('id');

            if (!$btn.data('original-html')) {
                $btn.data('original-html', $btn.html());
            }

            $btn.removeClass('btn-approve').addClass('btn-approve-load');
            $btn.html(`
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            `);

            try {
                await rpc('/leave/approve', { leave_id: leaveId });
                window.location.reload();
                return;
            } catch (error) {
                console.error("Failed to approve leave:", error);
                alert("An error occurred while approving the leave.");

                unlockLeaveActions();

                $btn.removeClass('btn-approve-load').addClass('btn-approve');
                if ($btn.data('original-html')) {
                    $btn.html($btn.data('original-html'));
                }
                return;
            }
        }

        if ($btn.hasClass('cancel-leave')) {
            if (leaveActionsLocked) {
                return;
            }

            const leaveId = $btn.data('leave-id');
            const leaveType = $btn.data('leave-type');
            const leaveDesc = $btn.data('leave-desc');
            const dateFrom = $btn.data('date-from');
            const dateTo = $btn.data('date-to');
            const duration = $btn.data('duration');
            const halfDay = $btn.data('half-day');

            $('#refuse_leave_id').val(leaveId);
            $('#refuse_time_off_type').val(leaveType || '');
            $('#refuse_desc').val(leaveDesc || '');
            $('#refuse_date_from').val(dateFrom || '');
            $('#refuse_date_to').val(dateTo || '');
            $('#refuse_duration').val(duration || '');
            $('#refuse_half_day')
                .prop('checked', !!halfDay)
                .prop('disabled', true);
            $('#refuse_reason').val('');
        }
    },
});

publicWidget.registry.LeaveRefuseModal = publicWidget.Widget.extend({
    selector: '#leaveRefuseModal',
    events: {
        'click #btn_refuse_leave': '_onRefuseClick',
    },

    async _onRefuseClick(ev) {
        ev.preventDefault();

        const $btn = $('#btn_refuse_leave');
        const leaveId = parseInt($('#refuse_leave_id').val());
        const reason = ($('#refuse_reason').val() || '').trim();

        if (!reason) {
            alert("Refuse reason is required.");
            return;
        }

        if (!lockLeaveActions()) {
            return;
        }

        if (!$btn.data('original-html')) {
            $btn.data('original-html', $btn.html());
        }
        $btn.prop('disabled', true);
        $btn.html(`
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Refusing...
        `);

        try {
            const res = await rpc('/my/leaves/refuse_leave', {
                leave_id: leaveId,
                refuse_reason: reason,
            });

            if (res && res.success) {
                window.location.reload();
            } else if (res && res.error) {
                alert(res.error);
                console.error(res.error);
            } else {
                alert("Unknown error.");
            }
        } catch (error) {
            console.error("Failed to refuse leave:", error);
            alert("An error occurred while refusing the leave.");
        } finally {
            unlockLeaveActions();
            $btn.prop('disabled', false);
            if ($btn.data('original-html')) {
                $btn.html($btn.data('original-html'));
            }
        }
    },
});

publicWidget.registry.LeaveFormSubmitOnce = publicWidget.Widget.extend({
    selector: '#leave_form',
    events: {
        submit: '_onSubmitOnce',
    },

    _onSubmitOnce(ev) {
        if (this._submitted) {
            ev.preventDefault();
            return;
        }
        this._submitted = true;

        const $submitBtn = $('#submit_leave_id');
        $submitBtn.prop('disabled', true);
        $submitBtn.addClass('disabled');

        const $discardBtn = $('#discard_form');
        $discardBtn.addClass('disabled');
        $discardBtn.css('pointer-events', 'none');
        $discardBtn.attr('aria-disabled', 'true');
    },
});

publicWidget.registry.LeaveBulkApprove = publicWidget.Widget.extend({
    selector: '.o_portal_wrap, #wrapwrap, body',
    events: {
        'change #select-all-leaves': '_onToggleSelectAll',
        'click #btn-approve-selected': '_onBulkApprove',
    },

    _onToggleSelectAll(ev) {
        const checked = ev.currentTarget.checked;
        $('.leave-select-checkbox').prop('checked', checked);
    },

    async _onBulkApprove(ev) {
        ev.preventDefault();

        const selectedIds = $('.leave-select-checkbox:checked')
            .map((i, el) => $(el).data('leave-id'))
            .get();

        if (!selectedIds.length) {
            alert("Please select at least one leave to approve.");
            return;
        }

        if (!lockLeaveActions()) {
            return;
        }

        const $btn = $('#btn-approve-selected');

        if (!$btn.data('original-html')) {
            $btn.data('original-html', $btn.html());
        }

        $btn.html(`
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Approving...
        `);

        try {
            await rpc('/leave/approve/bulk', {
                leave_ids: selectedIds,
            });

            window.location.reload();
        } catch (error) {
            console.error("Failed to bulk approve leaves:", error);
            alert("An error occurred while approving the selected leaves.");
        } finally {
            unlockLeaveActions();
            if ($btn.data('original-html')) {
                $btn.html($btn.data('original-html'));
            }
        }
    },
});
