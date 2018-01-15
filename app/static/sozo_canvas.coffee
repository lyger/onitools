# jQuery wrapper
(($) ->
  # document.ready
  $ ->
    ###----
    GLOBALS
    ----###

    # jQuery objects
    $canvas = $ "#draw"
    $textEdit = $ "#activeText"
    $undo = $ "#undobtn"
    $redo = $ "#redobtn"
    $download = $ "#downloadbtn"
    $share = $ "#sharebtn"

    # Meta options
    meta =
      canvasw: 800
      canvash: 600
      truew: 800
      trueh: 600
      minimapw: 188
      minimaph: 141
      backgroundColor: "#FFFFFF"

    # Load from passed options
    for prop, val of $canvas.data("metaOpts")
      meta[prop] = if isNaN(val) then val else parseInt(val)

    meta.msgColor = tinycolor.mostReadable(meta.backgroundColor, ["#000", "#FFF"]).toHexString()

    # These need to be set
    $canvas.css "background-color", meta.backgroundColor

    # Define a tinycolor object on the background color for later manipulation
    tc_bgcolor = tinycolor(meta.backgroundColor)
    darkenDesaturate = (tc, amt, darken=true) ->
      if darken
        tc.darken(amt).desaturate(amt).toHexString()
      else
        tc.lighten(amt).desaturate(amt).toHexString()

    # Load fonts
    fontList = ['Droid Sans', 'Droid Serif', 'Courgette', 'Source Code Pro', 'Indie Flower']
    WebFont.load({google: {families: fontList}})
    for f in fontList
      $ "<option name=\"" + f + "\">" + f + "</option>"
      .css "font-family", f
      .appendTo "#textfont"

    # Drawing modes enum
    MODE =
      NULL: -1
      UNDONE: 8
      PENCIL: 0
      ERASER: 1
      TEXT: 2
      BACKGROUND: 3
      FILL: 4
      IMAGE: 5

    # Current workspace state
    workspace =
      loading: false
      eraser: false
      drawing: false
      panning: false
      editing: false

    # Drawing options
    opts =
      color: "#000000"
      weight: 3
      fontFace: fontList[0]
      fontSize: 30
      minWeight: 1
      maxWeight: 50
      minFontSize: 10
      maxFontSize: 70

    ###--------------
    UTILITY FUNCTIONS
    --------------###
    # Sets cursor to end of contenteditable
    moveCursorToEnd = (elem) ->
      if document.createRange?
        range = document.createRange()
        range.selectNodeContents elem
        range.collapse false
        selection = window.getSelection()
        selection.removeAllRanges()
        selection.addRange range
      else if document.selection?
        range = document.body.createTextRange()
        range.moveToElementText elem
        range.collapse false
        range.select()

    ###-----------
    CANVAS OBJECTS
    -----------###
    class DrawingCanvas
      constructor: (@canvas, @scale, truewidth, trueheight) ->
        @width = @canvas.width
        @height = @canvas.height
        @scale = @scale ? 1
        @ctx = @canvas.getContext "2d"
        @truewidth = truewidth ? @width
        @trueheight = trueheight ? @height
        @panx = 0
        @pany = 0
        @refreshContext()

      # Reevaluate: IS THIS NECESSARY? Can be combined with drawLine, drawText etc?
      # As-is, this needs to be called when drawing interactively (TODO)
      changeOperation: (mode) ->
        switch mode
          when MODE.PENCIL, MODE.TEXT, MODE.FILL, MODE.IMAGE
            @ctx.globalCompositeOperation = "source-over"
          when MODE.ERASER
            @ctx.globalCompositeOperation = "destination-out"
          when MODE.BACKGROUND
            @ctx.globalCompositeOperation = "destination-over"

      refreshContext: ->
        @ctx.scale @scale, @scale
        @ctx.textAlign = "center";
        @ctx.textBaseline = "middle";

      initLine: (obj) ->
        @changeOperation obj.mode
        @ctx.strokeStyle = obj.color
        @ctx.lineWidth = obj.weight
        @ctx.moveTo obj.x0 - @panx, obj.y0 - @pany
        @ctx.beginPath()

      lineSegment: (x, y) ->
        @ctx.lineTo x - @panx, y - @pany
        @ctx.stroke()

      drawOne: (obj) ->
        @changeOperation obj.mode
        switch obj.mode
          when MODE.PENCIL, MODE.ERASER
            @initLine obj
            for x, i in obj.xs
              y = obj.ys[i]
              @lineSegment x, y
          when MODE.TEXT
            @ctx.fillStyle = obj.color
            @ctx.font = obj.font
            @ctx.fillText obj.text, obj.x0 - @panx, obj.y0 - @pany
          when MODE.IMAGE
            @ctx.putImageData obj.data, obj.x0 - @panx, obj.y0 - @pany

      draw: (data) ->
        @ctx.clearRect 0, 0, @width, @height
        for obj in data
          @drawOne obj
        return

      panBy: (dx, dy) ->
        @panx = Math.min Math.max(@panx + dx, 0), @truewidth - @width
        @pany = Math.min Math.max(@pany + dy, 0), @trueheight - @height

      colorAt: (x, y) ->
        @ctx.getImageData x, y, 1, 1
        .data

      toImageData: ->
        @ctx.getImageData 0, 0, @truewidth, @trueheight

    # Canvas objects
    minimapsc = Math.min meta.minimapw / meta.truew, meta.minimaph / meta.trueh

    mainCanvas = new DrawingCanvas $canvas[0], 1, meta.truew, meta.trueh
    virtCanvas = new DrawingCanvas $("<canvas>").attr(width: meta.truew, height: meta.trueh)[0]
    minimapCanvas = new DrawingCanvas $("#minimap").attr(width: minimapsc * meta.truew, \
                                                         height: minimapsc * meta.trueh) \
                                                   .css("background-color", darkenDesaturate(tc_bgcolor, 10))[0]
                                                   , minimapsc, meta.truew, meta.trueh
    saveCanvas = null

    # Specific properties for minimap
    minimapCanvas.defFillStyle = meta.backgroundColor
    minimapCanvas.defStrokeStyle = if tc_bgcolor.isLight() then \
                                    darkenDesaturate(tc_bgcolor, 30) else \
                                    darkenDesaturate(tc_bgcolor, 30, false)
    minimapCanvas.viewwidth = mainCanvas.width
    minimapCanvas.viewheight = mainCanvas.height
    minimapCanvas.width = meta.truew
    minimapCanvas.height = meta.trueh
    minimapCanvas.imageData = minimapCanvas.toImageData()

    minimapCanvas.safeDrawOne = (obj) ->
      @changeOperation MODE.PENCIL
      @ctx.putImageData @imageData, 0, 0
      @drawOne obj
      @imageData = @toImageData()

    # Define a special method to draw minimap
    minimapCanvas.drawMap = ->
      @ctx.clearRect 0, 0, @truewidth, @trueheight
      @changeOperation MODE.PENCIL
      @ctx.putImageData @imageData, 0, 0
      @changeOperation MODE.BACKGROUND
      @ctx.fillStyle = @defFillStyle
      @ctx.strokeStyle = @defStrokeStyle
      @ctx.fillRect mainCanvas.panx, mainCanvas.pany, @viewwidth, @viewheight
      @changeOperation MODE.PENCIL
      @ctx.lineWidth = 2 / minimapsc
      @ctx.beginPath()
      @ctx.rect mainCanvas.panx, mainCanvas.pany, @viewwidth, @viewheight
      @ctx.closePath()
      @ctx.stroke()

    ###-----
    SOCKETIO
    -----###
    canvas_id = window.location.pathname.split('/').pop()
    socket = io.connect location.protocol + '//' + document.domain + ':' + location.port + "/sozo"

    socket.on 'connect', ->
      socket.emit 'init canvas', {cid: canvas_id}

    drawStack =
      pending: 0
      top: 0
      data: []
      myActions: []
      undone: []
      redraw: (full=true)->
        if full
          @msg "Drawing..."
        setTimeout =>
          if full
            virtCanvas.draw @data
            minimapCanvas.draw @data
            minimapCanvas.imageData = minimapCanvas.toImageData()
          mainCanvas.draw [mode: MODE.IMAGE, data: virtCanvas.toImageData(), x0: 0, y0: 0]
          minimapCanvas.drawMap()
        , 1
      msg: (text) ->
        mainCanvas.ctx.clearRect 0, 0, mainCanvas.width, mainCanvas.height
        mainCanvas.changeOperation MODE.TEXT
        mainCanvas.ctx.fillStyle = meta.msgColor
        mainCanvas.ctx.font = "30px Droid Sans, sans-serif"
        mainCanvas.ctx.fillText text, mainCanvas.width / 2, mainCanvas.height / 2
      add: (obj) ->
        @addPending()
        socket.emit "draw action", {cid: canvas_id, obj: obj}
      update: (obj) ->
        @data.push obj
        virtCanvas.drawOne obj
        minimapCanvas.safeDrawOne obj
        @redraw(false) unless workspace.loading
        @top += 1
      undo: ->
        @addPending()
        socket.emit "undo", {cid: canvas_id}
      undoUpdate: (id) ->
        @data[id].mode += MODE.UNDONE
        @redraw()
      redo: ->
        @addPending()
        socket.emit "redo", {cid: canvas_id, id: @undone.pop()}
      redoUpdate: (obj) ->
        @data[obj.id] = obj
        @redraw()
      addPending: ->
        $undo.attr "disabled", true
        $redo.attr "disabled", true
        @pending += 1
      resolvePending: ->
        @pending -= 1
        if @pending == 0
          $undo.attr "disabled", @myActions.length == 0
          $redo.attr "disabled", @undone.length == 0

    socket.on "loading", ->
      workspace.loading = true

    socket.on "done loading", ->
      workspace.loading = false
      drawStack.redraw()

    socket.on "draw confirm", (msg) ->
      drawStack.undone.length = 0 # No more redo
      drawStack.myActions.push msg.id
      drawStack.resolvePending()

    socket.on "draw update", (obj) ->
      # Make sure no ids have been skipped
      if obj.id == drawStack.top
        drawStack.update obj
      # If not, ask for data to be resent from the top ID
      else if obj.id > drawStack.top
        socket.emit "resend", {cid: canvas_id, from: drawStack.top}

    socket.on "undo update", (msg) ->
      drawStack.undoUpdate msg.id

    socket.on "undo confirm", (msg) ->
      ix = drawStack.myActions.lastIndexOf msg.id
      drawStack.myActions.splice ix, 1 if ix > -1
      drawStack.undone.push msg.id
      drawStack.resolvePending()

    socket.on "redo update", (obj) ->
      drawStack.redoUpdate obj

    socket.on "redo confirm", (msg) ->
      drawStack.myActions.push msg.id
      drawStack.resolvePending()

    socket.on "reload", ->
      location.reload true

    ###------------
    UTILITY OBJECTS
    ------------###
    canvasOrigin =
      x: $canvas.offset().left
      y: $canvas.offset().top

    panTracker =
      lastx: 0
      lasty: 0
      refresh: (x, y) ->
        @lastx = x
        @lasty = y
      panCanvas: (x, y) ->
        dx = @lastx - x
        dy = @lasty - y
        @lastx = x
        @lasty = y
        # Resist the urge to make unnecessary generic functions! This is fine!
        mainCanvas.panBy dx, dy
        drawStack.redraw false

    breakpoint =
      value: null
      refreshAndResize: ->
        newvalue = window.getComputedStyle(document.querySelector('body'), ':before')
        .getPropertyValue('content').replace(/\"/g, '')
        if newvalue != @value
          newwidth = Math.min meta.truew, 600
          newheight = Math.min meta.trueh, 450
          switch newvalue
            when "desktop-up"
              newwidth = Math.min meta.truew, 880 
              newheight = Math.min meta.trueh, 495
            when "big-desktop-up"
              newwidth = Math.min meta.truew, 1280
              newheight = Math.min meta.trueh, 720
            when "hdpi-desktop-up"
              newwidth = Math.min meta.truew, 1920
              newheight = Math.min meta.trueh, 1080
          mainCanvas.canvas.width = mainCanvas.width = minimapCanvas.viewwidth = newwidth
          mainCanvas.canvas.height = mainCanvas.height = minimapCanvas.viewheight = newheight
          mainCanvas.refreshContext()
          panTracker.panCanvas 0, 0
          drawStack.redraw()
          @value = newvalue

    $ window
    .on 
      resize: (e) ->
        breakpoint.refreshAndResize()
        canvasOrigin.x = $canvas.offset().left
        canvasOrigin.y = $canvas.offset().top
      scroll: (e) ->
        canvasOrigin.x = $canvas.offset().left
        canvasOrigin.y = $canvas.offset().top
    .resize()

    activeLine =
      data: {}
      start: (x, y) ->
        x += mainCanvas.panx
        y += mainCanvas.pany
        @data =
          mode: if workspace.eraser then MODE.ERASER else MODE.PENCIL
          color: opts.color
          weight: opts.weight
          x0: x
          y0: y
          xs: []
          ys: []
          bb:
            minx: x - opts.weight / 2
            miny: y - opts.weight / 2
            maxx: x + opts.weight / 2
            maxy: y + opts.weight / 2
        mainCanvas.initLine @data
      segment: (x, y) ->
        x += mainCanvas.panx
        y += mainCanvas.pany
        @data.xs.push x
        @data.ys.push y
        @data.bb.minx = Math.min @data.bb.minx, x - @data.weight / 2
        @data.bb.miny = Math.min @data.bb.miny, y - @data.weight / 2
        @data.bb.maxx = Math.max @data.bb.maxx, x + @data.weight / 2
        @data.bb.maxy = Math.max @data.bb.maxy, y + @data.weight / 2
        mainCanvas.lineSegment x, y

    ###----------
    CANVAS EVENTS
    ----------###
    $canvas.on
      contextmenu: (e) ->
        false

      dblclick: (e) ->
        if workspace.loading
          return
        workspace.editing = true
        $textEdit
          .css
            left: e.pageX
            top: e.pageY
            color: opts.color
            "font-family": opts.fontFace
            "font-size": opts.fontSize
          .focus()
          .show()
        moveCursorToEnd $textEdit[0]

      mousedown: (e) ->
        if workspace.loading
          return
        switch e.which
          when 1
            if e.originalEvent.shiftKey # Pan key
              if not workspace.editing # Only allow pan when not editing
                workspace.panning = true
                panTracker.refresh e.pageX, e.pageY
            else
              workspace.drawing = true
              activeLine.start e.pageX - canvasOrigin.x, e.pageY - canvasOrigin.y
          when 3
            pickedColor = mainCanvas.colorAt e.pageX - canvasOrigin.x, e.pageY - canvasOrigin.y
            opts.color = if pickedColor[3] == 0 then meta.backgroundColor \
                         else tinycolor({r: pickedColor[0], g: pickedColor[1], b: pickedColor[2]}).toHexString()
            $ "#drawcolor"
            .val opts.color

      mousemove: (e) ->
        if workspace.drawing
          activeLine.segment e.pageX - canvasOrigin.x, e.pageY - canvasOrigin.y
        else if workspace.panning
          panTracker.panCanvas e.pageX, e.pageY

      "mouseup mouseout": (e) ->
        if workspace.drawing
          workspace.drawing = false
          if activeLine.data.xs.length > 0
            drawStack.add activeLine.data
        else if workspace.panning
          workspace.panning = false

    # Commit text
    $textEdit.on
      keypress: (e) ->
        if e.which == 13
          e.preventDefault()
          workspace.editing = false
          obj =
            mode: MODE.TEXT
            color: $textEdit.css "color"
            text: $textEdit.text().replace("\u200C", "")
            font: $textEdit.css("font-size") + " " + $textEdit.css("font-family")
            x0: parseInt($textEdit.css("left")) - canvasOrigin.x + mainCanvas.panx
            y0: parseInt($textEdit.css("top")) - canvasOrigin.y + mainCanvas.pany
          mainCanvas.drawOne obj
          drawStack.add obj
          this.innerHTML = "\u200C"
          $textEdit.hide()

    # Display hand for panning
    $ document
    .on
      keydown: (e) ->
        if e.which == 16 # Shift key
          $canvas.addClass if workspace.editing then "nopancanvas" else "pancanvas"
      keyup: (e) ->
        if e.which == 16 # Shift key
          $canvas.removeClass "pancanvas nopancanvas"

    ###----------
    BUTTON EVENTS
    ----------###
    $ "input[name=tool]:radio"
    .on "change", ->
      switch this.value
        when "pencil"
          $ "label[for=pencilwidth]"
          .text "Pencil weight"
          workspace.eraser = false
        when "eraser"
          $ "label[for=pencilwidth]"
          .text "Eraser weight"
          workspace.eraser = true

    $ "#pencilwidth"
    .attr
      min: opts.minWeight
      max: opts.maxWeight
      value: opts.weight
    .on
      input: ->
        opts.weight = Math.min Math.max(parseInt(this.value), opts.minWeight), opts.maxWeight
      change: ->
        this.value = opts.weight

    $ "#drawcolor"
    .on
      change: ->
        opts.color = this.value

    $ "#textsize"
    .attr
      min: opts.minFontSize
      max: opts.maxFontSize
      value: opts.fontSize
    .on
      input: ->
        opts.fontSize = Math.min Math.max(parseInt(this.value), opts.minFontSize), opts.maxFontSize
      change: ->
        this.value = opts.fontSize

    $ "#textfont"
    .css "font-family", fontList[0]
    .on "change", ->
      this.style.fontFamily = this.value;
      opts.fontFace = this.value;

    $ '[data-toggle="tooltip"]'
    .tooltip()

    $undo
    .on "click", ->
      drawStack.undo()

    $redo
    .on "click", ->
      drawStack.redo()

    $download
    .on "click", ->
      saveCanvas = saveCanvas ? new DrawingCanvas $("<canvas>").attr(width: meta.truew, height: meta.trueh)[0]
      saveCanvas.draw drawStack.data
      saveCanvas.changeOperation MODE.BACKGROUND
      saveCanvas.ctx.fillStyle = meta.backgroundColor
      saveCanvas.ctx.fillRect 0, 0, saveCanvas.truewidth, saveCanvas.trueheight
      this.href = saveCanvas.canvas.toDataURL "image/png"

    drawStack.msg "Loading..."

    $share
    .popover
      delay: {show: 0, hide: 1000}
      content: """
               <input id="sharefield" type="text" class="form-control" value="#{window.location.href}">
               <p>Link copied to clipboard.</p>
               """
    .on "click", ->
      $("#sharefield")[0].select()
      document.execCommand "Copy"
    
  return
) jQuery