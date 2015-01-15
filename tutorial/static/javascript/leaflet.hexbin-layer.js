L.HexLayer = L.Class.extend({
    includes: L.Mixin.Events,

    options: {
        minZoom: 0,
        maxZoom: 18,
        padding: 100,
        radius: 15
    },

    initialize: function (data, options) {
        var options = L.setOptions(this, options);
        this._layout = d3.hexbin()
	    .radius(this.options.radius)
	    .x( function(d) { return d['x']; } )
	    .y( function(d) { return d['y']; } )
	;
        this._data = data;
        this._levels = {};
    },

    onAdd: function (map) {
        this._map = map;

        // Create a container for svg.
        this._initContainer();

        // Set up events
        map.on({
            'moveend': this._update
        }, this);

        this._update();
    },

    onRemove: function (map) {
        this._container.parentNode.removeChild(this._container);

        map.off({
            'moveend': this._update
        }, this);

        this._container = null;
        this._map = null;
    },

    addTo: function (map) {
        map.addLayer(this);
        return this;
    },

    _initContainer: function () {
        var overlayPane = this._map.getPanes().overlayPane;
        if (!this._container || overlayPane.empty) {
            // TODO: Add optional ID attribute in the case of multiple layers.
            this._container = d3.select(overlayPane)
                .append('svg').attr('class', 'leaflet-layer leaflet-zoom-hide');
        }
    },

    dataBounds: function() {
	// calculates lat/long bounds of data, [[left,bottom],[right,top]]
	var d = this._data[0];
	var top = d['lat'];
	var bottom = d['lat'];
	var left = d['lng'];
	var right = d['lng'];
	for (i in this._data ) {
	    d = this._data[i];
	    top = Math.max(top, d['lat']);
	    bottom = Math.min(bottom, d['lat']);
	    left = Math.min(left,d['lng']);
	    right = Math.max(right,d['lng']);
	}
	// console.log("BLORP");
	// console.log( left );
	// console.log( right );
	// console.log( top );
	// console.log( bottom );
	// console.flush();
	return [[left,bottom],[right,top]];
    },

    _update: function () {

        if (!this._map) { return; }

        var zoom = this._map.getZoom();

        if (zoom > this.options.maxZoom || zoom < this.options.minZoom) {
            return;
        }

        var padding = this.options.padding,
            bounds = this._translateBounds(this.dataBounds());
            width = bounds.getSize().x + (2 * padding),
            height = bounds.getSize().y + (2 * padding),
            margin_top = bounds.min.y - padding,
            margin_left = bounds.min.x - padding;

        this._layout.size([width, height]);
        this._container.attr("width", width).attr("height", height)
            .style("margin-left", margin_left + "px").style("margin-top", margin_top + "px");

        if (!(zoom in this._levels)) {
            this._levels[zoom] = this._container.append("g").attr("class", "zoom-" + zoom);
            this._createHexagons(this._levels[zoom]);
            this._levels[zoom].attr("transform", "translate(" + -margin_left + "," + -margin_top + ")");
        }
        this._setLevel(zoom);
    },

    _setLevel: function (zoom) {
        if (this._currentLevel) {
            this._currentLevel.style("display", "none");
        }
        this._currentLevel = this._levels[zoom];
        this._currentLevel.style("display", "inline");
    },

    _createHexagons: function (container) {
        var layout = this._layout,
            data = this._data.map(function (d) {
		var point = this._project([d['lng'],d['lat']]);
		d['x'] = point[0];
		d['y'] = point[1];
                return d; //this._project([d['lng'],d['lat']]);
            }, this),
            bins = layout(data),
            hexagons = container.selectAll(".hexagon").data(bins);

        // Create hexagon elements when data is added.
        var path = hexagons.enter().append("path").attr("class", "hexagon");
        this._applyStyle(path);

        // Position hexagon elements.
        hexagons.attr("d", function (d) {
            // Setting "M" ensures each hexagon is drawn at its correct location.
            return "M" + d.x + "," + d.y + layout.hexagon();
        });
    },

    _applyStyle: function (hexagons) {
        if ('applyStyle' in this.options) {
            this.options.applyStyle.call(this, hexagons);
        }
    },

    _project: function (x) {
	// console.log(x);
	// console.flush();
        var point = this._map.latLngToLayerPoint([x[1], x[0]]);
        return [point.x, point.y];
    },

    _translateBounds: function (d3_bounds) {
	// console.log("translate");
	// console.flush();
        var nw = this._project([d3_bounds[0][0], d3_bounds[1][1]]),
            se = this._project([d3_bounds[1][0], d3_bounds[0][1]]);
        return L.bounds(nw, se);
    }

});

L.hexLayer = function (data, options) {
    return new L.HexLayer(data, options);
};
