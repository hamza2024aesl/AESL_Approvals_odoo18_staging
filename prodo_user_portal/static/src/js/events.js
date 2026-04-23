$(document).ready(function() {

    $('.collapse-content').hide();
    $('#work-card').show();

    $(document).on('click', '#create_revert_remarks', function(event) {
        event.preventDefault();
        $('#revert_form').addClass('element-to-hide-show').show();
    })

    $(document).on('click', '#discard_form', function(event) {
        event.preventDefault();
        $('#leave_form').hide();
        $('#loan_form').hide();
    })
});