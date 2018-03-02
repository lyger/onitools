// Generated by CoffeeScript 2.1.1
(function() {
  // jQuery wrapper
  (function($) {
    // document.ready
    $(function() {
      /*------------
      UTILITY OBJECTS
      ------------*/
      /*-----
      SOCKETIO
      -----*/
      var $canvas, $download, $redo, $share, $textEdit, $undo, DrawingCanvas, MODE, activeLine, breakpoint, canvasOrigin, canvas_id, darkenDesaturate, drawStack, f, fontList, j, len, mainCanvas, meta, minimapCanvas, minimapsc, moveCursorToEnd, opts, panTracker, prop, ref, saveCanvas, socket, tc_bgcolor, val, virtCanvas, workspace;
      /*----
      GLOBALS
      ----*/
      // jQuery objects
      $canvas = $("#draw");
      $textEdit = $("#activeText");
      $undo = $("#undobtn");
      $redo = $("#redobtn");
      $download = $("#downloadbtn");
      $share = $("#sharebtn");
      // Meta options
      meta = {
        canvasw: 800,
        canvash: 600,
        truew: 800,
        trueh: 600,
        minimapw: 188,
        minimaph: 141,
        backgroundColor: "#FFFFFF"
      };
      ref = $canvas.data("metaOpts");
      // Load from passed options
      for (prop in ref) {
        val = ref[prop];
        meta[prop] = isNaN(val) ? val : parseInt(val);
      }
      meta.msgColor = tinycolor.mostReadable(meta.backgroundColor, ["#000", "#FFF"]).toHexString();
      // These need to be set
      $canvas.css("background-color", meta.backgroundColor);
      // Define a tinycolor object on the background color for later manipulation
      tc_bgcolor = tinycolor(meta.backgroundColor);
      darkenDesaturate = function(tc, amt, darken = true) {
        if (darken) {
          return tc.darken(amt).desaturate(amt).toHexString();
        } else {
          return tc.lighten(amt).desaturate(amt).toHexString();
        }
      };
      // Load fonts
      fontList = ['Droid Sans', 'Droid Serif', 'Courgette', 'Source Code Pro', 'Indie Flower'];
      WebFont.load({
        google: {
          families: fontList
        }
      });
      for (j = 0, len = fontList.length; j < len; j++) {
        f = fontList[j];
        $("<option name=\"" + f + "\">" + f + "</option>").css("font-family", f).appendTo("#textfont");
      }
      // Drawing modes enum
      MODE = {
        NULL: -1,
        UNDONE: 8,
        PENCIL: 0,
        ERASER: 1,
        TEXT: 2,
        BACKGROUND: 3,
        FILL: 4,
        IMAGE: 5
      };
      // Current workspace state
      workspace = {
        loading: false,
        eraser: false,
        drawing: false,
        panning: false,
        editing: false
      };
      // Drawing options
      opts = {
        color: "#000000",
        weight: 3,
        fontFace: fontList[0],
        fontSize: 30,
        minWeight: 1,
        maxWeight: 50,
        minFontSize: 10,
        maxFontSize: 70
      };
      /*--------------
      UTILITY FUNCTIONS
      --------------*/
      // Sets cursor to end of contenteditable
      moveCursorToEnd = function(elem) {
        var range, selection;
        if (document.createRange != null) {
          range = document.createRange();
          range.selectNodeContents(elem);
          range.collapse(false);
          selection = window.getSelection();
          selection.removeAllRanges();
          return selection.addRange(range);
        } else if (document.selection != null) {
          range = document.body.createTextRange();
          range.moveToElementText(elem);
          range.collapse(false);
          return range.select();
        }
      };
      /*-----------
      CANVAS OBJECTS
      -----------*/
      DrawingCanvas = class DrawingCanvas {
        constructor(canvas, scale, truewidth, trueheight) {
          var ref1;
          this.canvas = canvas;
          this.scale = scale;
          this.width = this.canvas.width;
          this.height = this.canvas.height;
          this.scale = (ref1 = this.scale) != null ? ref1 : 1;
          this.ctx = this.canvas.getContext("2d");
          this.truewidth = truewidth != null ? truewidth : this.width;
          this.trueheight = trueheight != null ? trueheight : this.height;
          this.panx = 0;
          this.pany = 0;
          this.refreshContext();
        }

        // Reevaluate: IS THIS NECESSARY? Can be combined with drawLine, drawText etc?
        // As-is, this needs to be called when drawing interactively (TODO)
        changeOperation(mode) {
          switch (mode) {
            case MODE.PENCIL:
            case MODE.TEXT:
            case MODE.FILL:
            case MODE.IMAGE:
              return this.ctx.globalCompositeOperation = "source-over";
            case MODE.ERASER:
              return this.ctx.globalCompositeOperation = "destination-out";
            case MODE.BACKGROUND:
              return this.ctx.globalCompositeOperation = "destination-over";
          }
        }

        refreshContext() {
          this.ctx.scale(this.scale, this.scale);
          this.ctx.textAlign = "center";
          return this.ctx.textBaseline = "middle";
        }

        initLine(obj) {
          this.changeOperation(obj.mode);
          this.ctx.strokeStyle = obj.color;
          this.ctx.lineWidth = obj.weight;
          this.ctx.moveTo(obj.x0 - this.panx, obj.y0 - this.pany);
          return this.ctx.beginPath();
        }

        lineSegment(x, y) {
          this.ctx.lineTo(x - this.panx, y - this.pany);
          return this.ctx.stroke();
        }

        drawOne(obj) {
          var i, k, len1, ref1, results, x, y;
          this.changeOperation(obj.mode);
          switch (obj.mode) {
            case MODE.PENCIL:
            case MODE.ERASER:
              this.initLine(obj);
              ref1 = obj.xs;
              results = [];
              for (i = k = 0, len1 = ref1.length; k < len1; i = ++k) {
                x = ref1[i];
                y = obj.ys[i];
                results.push(this.lineSegment(x, y));
              }
              return results;
              break;
            case MODE.TEXT:
              this.ctx.fillStyle = obj.color;
              this.ctx.font = obj.font;
              return this.ctx.fillText(obj.text, obj.x0 - this.panx, obj.y0 - this.pany);
            case MODE.IMAGE:
              return this.ctx.putImageData(obj.data, obj.x0 - this.panx, obj.y0 - this.pany);
          }
        }

        draw(data) {
          var k, len1, obj;
          this.ctx.clearRect(0, 0, this.width, this.height);
          for (k = 0, len1 = data.length; k < len1; k++) {
            obj = data[k];
            this.drawOne(obj);
          }
        }

        panBy(dx, dy) {
          this.panx = Math.min(Math.max(this.panx + dx, 0), this.truewidth - this.width);
          return this.pany = Math.min(Math.max(this.pany + dy, 0), this.trueheight - this.height);
        }

        colorAt(x, y) {
          return this.ctx.getImageData(x, y, 1, 1).data;
        }

        toImageData() {
          return this.ctx.getImageData(0, 0, this.truewidth, this.trueheight);
        }

      };
      // Canvas objects
      minimapsc = Math.min(meta.minimapw / meta.truew, meta.minimaph / meta.trueh);
      mainCanvas = new DrawingCanvas($canvas[0], 1, meta.truew, meta.trueh);
      virtCanvas = new DrawingCanvas($("<canvas>").attr({
        width: meta.truew,
        height: meta.trueh
      })[0]);
      minimapCanvas = new DrawingCanvas($("#minimap").attr({
        width: minimapsc * meta.truew,
        height: minimapsc * meta.trueh
      }).css("background-color", darkenDesaturate(tc_bgcolor, 10))[0], minimapsc, meta.truew, meta.trueh);
      saveCanvas = null;
      // Specific properties for minimap
      minimapCanvas.defFillStyle = meta.backgroundColor;
      minimapCanvas.defStrokeStyle = tc_bgcolor.isLight() ? darkenDesaturate(tc_bgcolor, 30) : darkenDesaturate(tc_bgcolor, 30, false);
      minimapCanvas.viewwidth = mainCanvas.width;
      minimapCanvas.viewheight = mainCanvas.height;
      minimapCanvas.width = meta.truew;
      minimapCanvas.height = meta.trueh;
      minimapCanvas.imageData = minimapCanvas.toImageData();
      minimapCanvas.safeDrawOne = function(obj) {
        this.changeOperation(MODE.PENCIL);
        this.ctx.putImageData(this.imageData, 0, 0);
        this.drawOne(obj);
        return this.imageData = this.toImageData();
      };
      // Define a special method to draw minimap
      minimapCanvas.drawMap = function() {
        this.ctx.clearRect(0, 0, this.truewidth, this.trueheight);
        this.changeOperation(MODE.PENCIL);
        this.ctx.putImageData(this.imageData, 0, 0);
        this.changeOperation(MODE.BACKGROUND);
        this.ctx.fillStyle = this.defFillStyle;
        this.ctx.strokeStyle = this.defStrokeStyle;
        this.ctx.fillRect(mainCanvas.panx, mainCanvas.pany, this.viewwidth, this.viewheight);
        this.changeOperation(MODE.PENCIL);
        this.ctx.lineWidth = 2 / minimapsc;
        this.ctx.beginPath();
        this.ctx.rect(mainCanvas.panx, mainCanvas.pany, this.viewwidth, this.viewheight);
        this.ctx.closePath();
        return this.ctx.stroke();
      };
      canvas_id = window.location.pathname.split('/').pop();
      socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + "/sozo");
      socket.on('connect', function() {
        return socket.emit('init canvas', {
          cid: canvas_id
        });
      });
      drawStack = {
        pending: 0,
        top: 0,
        data: [],
        myActions: [],
        undone: [],
        redraw: function(full = true) {
          if (full) {
            this.msg("Drawing...");
          }
          return setTimeout(() => {
            if (full) {
              virtCanvas.draw(this.data);
              minimapCanvas.draw(this.data);
              minimapCanvas.imageData = minimapCanvas.toImageData();
            }
            mainCanvas.draw([
              {
                mode: MODE.IMAGE,
                data: virtCanvas.toImageData(),
                x0: 0,
                y0: 0
              }
            ]);
            return minimapCanvas.drawMap();
          }, 1);
        },
        msg: function(text) {
          mainCanvas.ctx.clearRect(0, 0, mainCanvas.width, mainCanvas.height);
          mainCanvas.changeOperation(MODE.TEXT);
          mainCanvas.ctx.fillStyle = meta.msgColor;
          mainCanvas.ctx.font = "30px Droid Sans, sans-serif";
          return mainCanvas.ctx.fillText(text, mainCanvas.width / 2, mainCanvas.height / 2);
        },
        add: function(obj) {
          this.addPending();
          return socket.emit("draw action", {
            cid: canvas_id,
            obj: obj
          });
        },
        update: function(obj) {
          this.data.push(obj);
          virtCanvas.drawOne(obj);
          minimapCanvas.safeDrawOne(obj);
          if (!workspace.loading) {
            this.redraw(false);
          }
          return this.top += 1;
        },
        undo: function() {
          this.addPending();
          return socket.emit("undo", {
            cid: canvas_id
          });
        },
        undoUpdate: function(id) {
          this.data[id].mode += MODE.UNDONE;
          return this.redraw();
        },
        redo: function() {
          this.addPending();
          return socket.emit("redo", {
            cid: canvas_id,
            id: this.undone.pop()
          });
        },
        redoUpdate: function(obj) {
          this.data[obj.id] = obj;
          return this.redraw();
        },
        addPending: function() {
          $undo.attr("disabled", true);
          $redo.attr("disabled", true);
          return this.pending += 1;
        },
        resolvePending: function() {
          this.pending -= 1;
          if (this.pending === 0) {
            $undo.attr("disabled", this.myActions.length === 0);
            return $redo.attr("disabled", this.undone.length === 0);
          }
        }
      };
      socket.on("loading", function() {
        return workspace.loading = true;
      });
      socket.on("done loading", function() {
        workspace.loading = false;
        return drawStack.redraw();
      });
      socket.on("draw confirm", function(msg) {
        drawStack.undone.length = 0; // No more redo
        drawStack.myActions.push(msg.id);
        return drawStack.resolvePending();
      });
      socket.on("draw update", function(obj) {
        // Make sure no ids have been skipped
        if (obj.id === drawStack.top) {
          return drawStack.update(obj);
        // If not, ask for data to be resent from the top ID
        } else if (obj.id > drawStack.top) {
          return socket.emit("resend", {
            cid: canvas_id,
            from: drawStack.top
          });
        }
      });
      socket.on("undo update", function(msg) {
        return drawStack.undoUpdate(msg.id);
      });
      socket.on("undo confirm", function(msg) {
        var ix;
        ix = drawStack.myActions.lastIndexOf(msg.id);
        if (ix > -1) {
          drawStack.myActions.splice(ix, 1);
        }
        drawStack.undone.push(msg.id);
        return drawStack.resolvePending();
      });
      socket.on("redo update", function(obj) {
        return drawStack.redoUpdate(obj);
      });
      socket.on("redo confirm", function(msg) {
        drawStack.myActions.push(msg.id);
        return drawStack.resolvePending();
      });
      socket.on("reload", function() {
        return location.reload(true);
      });
      canvasOrigin = {
        x: $canvas.offset().left,
        y: $canvas.offset().top
      };
      panTracker = {
        lastx: 0,
        lasty: 0,
        refresh: function(x, y) {
          this.lastx = x;
          return this.lasty = y;
        },
        panCanvas: function(x, y) {
          var dx, dy;
          dx = this.lastx - x;
          dy = this.lasty - y;
          this.lastx = x;
          this.lasty = y;
          // Resist the urge to make unnecessary generic functions! This is fine!
          mainCanvas.panBy(dx, dy);
          return drawStack.redraw(false);
        }
      };
      breakpoint = {
        value: null,
        refreshAndResize: function() {
          var newheight, newvalue, newwidth;
          newvalue = window.getComputedStyle(document.querySelector('body'), ':before').getPropertyValue('content').replace(/\"/g, '');
          if (newvalue !== this.value) {
            newwidth = Math.min(meta.truew, 600);
            newheight = Math.min(meta.trueh, 450);
            switch (newvalue) {
              case "desktop-up":
                newwidth = Math.min(meta.truew, 880);
                newheight = Math.min(meta.trueh, 495);
                break;
              case "big-desktop-up":
                newwidth = Math.min(meta.truew, 1280);
                newheight = Math.min(meta.trueh, 720);
                break;
              case "hdpi-desktop-up":
                newwidth = Math.min(meta.truew, 1920);
                newheight = Math.min(meta.trueh, 1080);
            }
            mainCanvas.canvas.width = mainCanvas.width = minimapCanvas.viewwidth = newwidth;
            mainCanvas.canvas.height = mainCanvas.height = minimapCanvas.viewheight = newheight;
            mainCanvas.refreshContext();
            panTracker.panCanvas(0, 0);
            drawStack.redraw();
            return this.value = newvalue;
          }
        }
      };
      $(window).on({
        resize: function(e) {
          breakpoint.refreshAndResize();
          canvasOrigin.x = $canvas.offset().left;
          return canvasOrigin.y = $canvas.offset().top;
        },
        scroll: function(e) {
          canvasOrigin.x = $canvas.offset().left;
          return canvasOrigin.y = $canvas.offset().top;
        }
      }).resize();
      activeLine = {
        data: {},
        start: function(x, y) {
          x += mainCanvas.panx;
          y += mainCanvas.pany;
          this.data = {
            mode: workspace.eraser ? MODE.ERASER : MODE.PENCIL,
            color: opts.color,
            weight: opts.weight,
            x0: x,
            y0: y,
            xs: [],
            ys: [],
            bb: {
              minx: x - opts.weight / 2,
              miny: y - opts.weight / 2,
              maxx: x + opts.weight / 2,
              maxy: y + opts.weight / 2
            }
          };
          return mainCanvas.initLine(this.data);
        },
        segment: function(x, y) {
          x += mainCanvas.panx;
          y += mainCanvas.pany;
          this.data.xs.push(x);
          this.data.ys.push(y);
          this.data.bb.minx = Math.min(this.data.bb.minx, x - this.data.weight / 2);
          this.data.bb.miny = Math.min(this.data.bb.miny, y - this.data.weight / 2);
          this.data.bb.maxx = Math.max(this.data.bb.maxx, x + this.data.weight / 2);
          this.data.bb.maxy = Math.max(this.data.bb.maxy, y + this.data.weight / 2);
          return mainCanvas.lineSegment(x, y);
        }
      };
      /*----------
      CANVAS EVENTS
      ----------*/
      $canvas.on({
        contextmenu: function(e) {
          return false;
        },
        dblclick: function(e) {
          if (workspace.loading) {
            return;
          }
          workspace.editing = true;
          $textEdit.css({
            left: e.pageX,
            top: e.pageY,
            color: opts.color,
            "font-family": opts.fontFace,
            "font-size": opts.fontSize
          }).focus().show();
          return moveCursorToEnd($textEdit[0]);
        },
        mousedown: function(e) {
          var pickedColor;
          if (workspace.loading) {
            return;
          }
          switch (e.which) {
            case 1:
              if (e.originalEvent.shiftKey) { // Pan key
                if (!workspace.editing) { // Only allow pan when not editing
                  workspace.panning = true;
                  return panTracker.refresh(e.pageX, e.pageY);
                }
              } else {
                workspace.drawing = true;
                return activeLine.start(e.pageX - canvasOrigin.x, e.pageY - canvasOrigin.y);
              }
              break;
            case 3:
              pickedColor = mainCanvas.colorAt(e.pageX - canvasOrigin.x, e.pageY - canvasOrigin.y);
              opts.color = pickedColor[3] === 0 ? meta.backgroundColor : tinycolor({
                r: pickedColor[0],
                g: pickedColor[1],
                b: pickedColor[2]
              }).toHexString();
              return $("#drawcolor").val(opts.color);
          }
        },
        mousemove: function(e) {
          if (workspace.drawing) {
            return activeLine.segment(e.pageX - canvasOrigin.x, e.pageY - canvasOrigin.y);
          } else if (workspace.panning) {
            return panTracker.panCanvas(e.pageX, e.pageY);
          }
        },
        "mouseup mouseout": function(e) {
          if (workspace.drawing) {
            workspace.drawing = false;
            if (activeLine.data.xs.length > 0) {
              return drawStack.add(activeLine.data);
            }
          } else if (workspace.panning) {
            return workspace.panning = false;
          }
        }
      });
      // Commit text
      $textEdit.on({
        keypress: function(e) {
          var obj;
          if (e.which === 13) {
            e.preventDefault();
            workspace.editing = false;
            obj = {
              mode: MODE.TEXT,
              color: $textEdit.css("color"),
              text: $textEdit.text().replace("\u200C", ""),
              font: $textEdit.css("font-size") + " " + $textEdit.css("font-family"),
              x0: parseInt($textEdit.css("left")) - canvasOrigin.x + mainCanvas.panx,
              y0: parseInt($textEdit.css("top")) - canvasOrigin.y + mainCanvas.pany
            };
            mainCanvas.drawOne(obj);
            drawStack.add(obj);
            this.innerHTML = "\u200C";
            return $textEdit.hide();
          }
        }
      });
      // Display hand for panning
      $(document).on({
        keydown: function(e) {
          if (e.which === 16) { // Shift key
            return $canvas.addClass(workspace.editing ? "nopancanvas" : "pancanvas");
          }
        },
        keyup: function(e) {
          if (e.which === 16) { // Shift key
            return $canvas.removeClass("pancanvas nopancanvas");
          }
        }
      });
      /*----------
      BUTTON EVENTS
      ----------*/
      $("input[name=tool]:radio").on("change", function() {
        switch (this.value) {
          case "pencil":
            $("label[for=pencilwidth]").text("Pencil weight");
            return workspace.eraser = false;
          case "eraser":
            $("label[for=pencilwidth]").text("Eraser weight");
            return workspace.eraser = true;
        }
      });
      $("#pencilwidth").attr({
        min: opts.minWeight,
        max: opts.maxWeight,
        value: opts.weight
      }).on({
        input: function() {
          return opts.weight = Math.min(Math.max(parseInt(this.value), opts.minWeight), opts.maxWeight);
        },
        change: function() {
          return this.value = opts.weight;
        }
      });
      $("#drawcolor").on({
        change: function() {
          return opts.color = this.value;
        }
      });
      $("#textsize").attr({
        min: opts.minFontSize,
        max: opts.maxFontSize,
        value: opts.fontSize
      }).on({
        input: function() {
          return opts.fontSize = Math.min(Math.max(parseInt(this.value), opts.minFontSize), opts.maxFontSize);
        },
        change: function() {
          return this.value = opts.fontSize;
        }
      });
      $("#textfont").css("font-family", fontList[0]).on("change", function() {
        this.style.fontFamily = this.value;
        return opts.fontFace = this.value;
      });
      $('[data-toggle="tooltip"]').tooltip();
      $undo.on("click", function() {
        return drawStack.undo();
      });
      $redo.on("click", function() {
        return drawStack.redo();
      });
      $download.on("click", function() {
        saveCanvas = saveCanvas != null ? saveCanvas : new DrawingCanvas($("<canvas>").attr({
          width: meta.truew,
          height: meta.trueh
        })[0]);
        saveCanvas.draw(drawStack.data);
        saveCanvas.changeOperation(MODE.BACKGROUND);
        saveCanvas.ctx.fillStyle = meta.backgroundColor;
        saveCanvas.ctx.fillRect(0, 0, saveCanvas.truewidth, saveCanvas.trueheight);
        return this.href = saveCanvas.canvas.toDataURL("image/png");
      });
      drawStack.msg("Loading...");
      return $share.popover({
        delay: {
          show: 0,
          hide: 1000
        },
        content: `<input id="sharefield" type="text" class="form-control" value="${window.location.href}">\n<p>Link copied to clipboard.</p>`
      }).on("click", function() {
        $("#sharefield")[0].select();
        return document.execCommand("Copy");
      });
    });
  })(jQuery);

}).call(this);