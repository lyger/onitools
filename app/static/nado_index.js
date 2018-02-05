(function($) {
  $(function() {
    var socket, genNum, genCat, genName, $genSelect, $numSelect, $genButton, $nameList, $custField, $custButton, $custForm;
    socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + "/nado");

    genNum = 10;
    genCat = null;
    genName = null;

    $genSelect = $('#nadoGenerator');
    $numSelect = $('#nadoNumber');
    $genButton = $('#nadoSubmit');
    $nameList = $('#nadoNames');
    $custField = $('#nadoSuggestText');
    $custButton = $('#nadoSuggestBtn');
    $custForm = $('#nadoSuggestForm');

    $genSelect.val('NULLOPTION');
    $numSelect.val(genNum);

    function syncButtonState() {
      $genButton.text('Generate');
      $genButton.attr('disabled', (genCat === null) && (genName === null))
    }

    syncButtonState();

    socket.on('names sent', function(msg) {
      $nameList.empty();
      let names = msg.names;
      names.forEach(function(name) {
        $nameList.append($('<li>', {'class': 'list-group-item'}).text(name)
          // Vote up button.
          .append($('<button>', {'class': 'btn btn-sm btn-link text-success', 'type': 'button'})
            .css({'padding-right': '0.1rem'})
            .on('click', function() {
              this.disabled = true;
              $(this).next().attr('disabled', true).removeClass('text-danger').addClass('text-secondary');
              socket.emit('vote', {'category': msg.category, 'generator': msg.generator, 'name': name, 'up': true});
            })
            .append($('<i>', {'class': 'fa fa-thumbs-up', 'aria-hidden': 'true'})))
          // Vote down button.
          .append($('<button>', {'class': 'btn btn-sm btn-link text-danger', 'type': 'button'})
            .css({'padding-left': '0.1rem'})
            .on('click', function() {
              this.disabled = true;
              $(this).prev().attr('disabled', true).removeClass('text-success').addClass('text-secondary');
              socket.emit('vote', {'category': msg.category, 'generator': msg.generator, 'name': name, 'up': false});
            })
            .append($('<i>', {'class': 'fa fa-thumbs-down', 'aria-hidden': 'true'})))
          );
      });
      
      $custForm.show();

      $custButton.off();
      $custButton.on('click', function(e) {
        $custForm.hide();
        let newName = $custField.val();
        if(newName.length > 0) {
          socket.emit('add custom', {'category': msg.category, 'generator': msg.generator, 'name': newName});
        }
        $custField.val('');
        this.disabled = true;
      });

      setTimeout(syncButtonState, 1000);
    });

    socket.on('busy', function() {
      $nameList.empty();
      $nameList.append($('<li>', {'class': 'list-group-item'})
        .text('Server is busy. Please wait a moment and try again.'));
      setTimeout(syncButtonState, 1000);
    });

    $numSelect.on('change', function(e) {
      genNum = parseInt(this.value);
    });

    $genSelect.on('change', function(e) {
      var selected = $(':selected', this);
      genCat = selected.parent().attr('label');
      genName = this.value;
      syncButtonState();
    });

    $genButton.on('click', function(e) {
      this.disabled = true;
      this.textContent = 'Please wait...';
      $custForm.hide();
      socket.emit('send names', {category: genCat, generator: genName, number: genNum});
    });

    $custField.on('input change', function(e) {
      $custButton.attr('disabled', this.value.length === 0);
    });
  });
})(jQuery);