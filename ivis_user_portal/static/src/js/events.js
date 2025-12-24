$(document).ready(function() {

    $('.collapse-content').hide();
    $('#work-card').show();

    // Event handler for click events on <a> tags with class 'acol'
    $(document).on('click', 'a.acol', function(event) {
        event.preventDefault(); // Preventing the default behavior of the anchor link

        // Can also redirect to the href if needed
        // window.location.href = $(this).attr('href');

        var target = $(this).attr('href'); // Get the target section
        $('.collapse-content').hide(); // Hide all sections
        $(target).show(); // Show the target section
    });

    $(document).on('click', '#create_leave', function(event) {
        event.preventDefault();
        $('#leave_form').addClass('element-to-hide-show').show();
    })
//    $(document).on('click', '#create_revert_remarks', function(event) {
//    debugger;
//        event.preventDefault();
//        $('#revert_form').addClass('element-to-hide-show').show();
//    })

    $(document).on('click', '#create_loan', function(event) {
        event.preventDefault();
        $('#loan_form').addClass('element-to-hide-show').show();
    })

    $(document).on('click', '#discard_form', function(event) {
        event.preventDefault();
        $('#leave_form').hide();
        $('#loan_form').hide();
    })
});