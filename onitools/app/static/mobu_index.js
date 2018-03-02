(function($) {
	$("#mobuName")
	.on("change input", function(e) {
		this.value = this.value.replace(/[^A-Za-z0-9_]+/g, "");
		if(this.value.length < 1) $("#mobuSubmit").prop("disabled", true);
		else $("#mobuSubmit").prop("disabled", false);
	});
})(jQuery);