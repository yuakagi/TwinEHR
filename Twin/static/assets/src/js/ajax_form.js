// Scripts for handling AJAX form requests.

/*
 * Fetch CSRF token from cookies.
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/*
 * Handle form submission with AJAX.
 * @param {string} url - The URL to send the request to.
 * @param {string} formId - The ID of the form being submitted (e.g., "ajaxForm").
 * @param {function} successfn - Callback function on success. 
 *  JSON response data is passed to this function as successfn(data).
 * @param {function} [errorfn] - Callback function on error (optional).
 *  This function expects arguments like 'errorfn(xhr, status, error)'.
 * @param {function} [alwaysfn] - Callback function to execute always (optional).
 *  This function does not take arguments by default.
 */
function handleAjaxForm(url, formId, successfn, errorfn = function () {}, alwaysfn = function () {}) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    $.ajax({
        url: url,
        type: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
        },
        data: formData,
        processData: false,
        contentType: false,
        dataType: "json",

        // Show loading indicator before request
        beforeSend: function () {
            Swal.fire({
                title: "Processing...",
                html: "Please wait.",
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
        },

        // Successful AJAX response
        success: function (data) {
            // Reset previous validations
            resetFormValidation($(form));
            // Execute function for AJAX success
            successfn(data);
            // Show messages if found
            if (data.messages && data.messages.length > 0) {
                Swal.fire({
                    icon: "info",
                    title: "Note",
                    html: data.messages.join("<br>"),
                    confirmButtonText: "Close"
                });
            }
        },

        // Failed AJAX response
        error: function (xhr, status, error) {
            // Logging errors
            console.error("Error fetching data:", status, error);
            // Reset previous validations
            if (xhr.responseJSON && xhr.responseJSON.form_errors) {
                applyFormValidation(xhr.responseJSON.form_errors);
            }
            // Execute function for failed AJAX 
            errorfn(xhr, status, error); // This will be ignored if errorfn is not provided
            // Show messages if found
            if (xhr.responseJSON && xhr.responseJSON.messages && xhr.responseJSON.messages.length > 0) {
                Swal.fire({
                    icon: "error",
                    title: "Error",
                    html: xhr.responseJSON.messages.join("<br>"),
                    confirmButtonText: "Close"
                });
            }
        }
    }).always(function () {
        Swal.close();
        alwaysfn();
    });
}

/**
 * Apply form validation errors to the corresponding fields.
 * @param {Object} form - JSON object containing field errors.
 */
function applyFormValidation(form_errors) {
    Object.keys(form_errors).forEach(function (fieldName) {
        let field = $("[name='" + fieldName + "']");
        let fieldId = field.attr("id");
        if (!fieldId) return;
        let feedback = $("#" + fieldId + "-feedback");

        field.addClass("is-invalid").removeClass("is-valid");

        if (feedback.length) {
            feedback.text(form_errors[fieldName][0]); // Show first error message
        } else {
            // Dynamically insert feedback if it does not exist
            field.after(`<div id="${field.attr("id")}-feedback" class="invalid-feedback">${form_errors[fieldName][0]}</div>`);

        }
    });
}

/**
 * Reset form validation styles and messages.
 * @param {jQuery} form - jQuery object of the form.
 */
function resetFormValidation(form) {
    $(form).find(".form-control, .form-select, .form-check-input, .form-check").removeClass("is-invalid is-valid");
    $(form).find(".invalid-feedback").text("");
}