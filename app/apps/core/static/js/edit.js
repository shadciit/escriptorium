var panels = {};
var API = {
    document: '/api/documents/' + DOCUMENT_ID,
    part: '/api/documents/' + DOCUMENT_ID + '/parts/{part_pk}/'
};

var zoom = new WheelZoom();
var undoManager = new UndoManager();
var fullSizeImgLoaded = false;
function preloadImage(url, callback) {
    var img=new Image();
    img.src=url;
    img.onload = callback;
}


$(document).ready(function() {
    function makePanel(name, class_, visible) {
	    var title = name + '-panel';
	    var show = Cookies.get(title) && JSON.parse(Cookies.get(title));
	    panels[name] = new class_($('#'+title), $('#'+name+'-tools'), show);
	    if (show) {
	        $('#'+title+'-btn').addClass('btn-primary').removeClass('btn-secondary');
	    }
	}
	makePanel('source', SourcePanel);
	makePanel('seg', SegmentationPanel);
	makePanel('trans', TranscriptionPanel);

    var current_part = null;
    
    function loadPart(pk, callback) {
        let uri = API.part.replace('{part_pk}', pk);
        $.get(uri, function(data) {
            for (var key in panels) {
                panels[key].load(data);
            }
            current_part = data;
            
            /* previous and next button */
            window.history.pushState({},"", document.location.href.replace(/(part\/)\d+(\/edit)/, '$1'+data.pk+'$2'));
            if (data.previous) $('a#prev-part').data('target', data.previous).show();
            else $('a#prev-part').hide();
            if (data.next) $('a#next-part').data('target', data.next).show();
            else $('a#next-part').hide();
            $('#part-name').html(data.title);
            $('#part-filename').html(data.filename+' ('+ data.image.size[0]+'x'+data.image.size[1]+')');
            
            // set the 'image' tab btn to select the corresponding image
            var tabUrl = new URL($('#images-tab-link').attr('href'), window.location.origin);
            tabUrl.searchParams.set('select', pk);
            $('#images-tab-link').attr('href', tabUrl);
            
            if (callback) callback(data);
        });
    }
    
    $('.open-panel').on('click', function(ev) {
        $(this).toggleClass('btn-primary').toggleClass('btn-secondary');
        var panel = $(this).data('target');
        panels[panel].toggle();
        for (var key in panels) {
            panels[key].refresh();
        }
    });
    
    // previous and next buttons
    $('a#prev-part, a#next-part').click(function(ev) {
        ev.preventDefault();
        var pk = $(this).data('target');
        loadPart(pk);
    });
    document.addEventListener('keydown', function(event) {
        if (event.keyCode == 33) {  // page up
            $('a#prev-part').click();
            event.preventDefault();
        } else if (event.keyCode == 34) {  // page down
            $('a#next-part').click();
            event.preventDefault();
        }
    });
    
    loadPart(PART_ID, function(data) {
        undoManager.clear();
        fullSizeImgLoaded = false;
    });
    
    // zoom slider
    $('#zoom-range').attr('min', zoom.minScale);
    $('#zoom-range').attr('max', zoom.maxScale);
    $('#zoom-range').val(zoom.scale);
    
    // zoom.events.addEventListener('wheelzoom.updated', function(data) {
    //     if (current_part !== null && zoom.scale > 1) {
    //         // zooming in, load the full size image if it's not done already to make sure the resolution is good enough to read stuff..
    //         preloadImage(current_part.image.uri, function() {
    //             panels['source'].$img.attr('src', this.src);
    //             panels['source'].refresh();  // doesn't do anything for now but might in the future
    //             if (panels['seg'].colorMode == 'color') {
    //                 panels['seg'].$img.attr('src', this.src);
    //                 panels['seg'].refresh();
    //             }
    //         });
    //     }
    //     $('#zoom-range').val(zoom.scale);
    // });
    
    $('#zoom-range').on('input', function(ev) {
        let openPanel = panels[Object.keys(panels).find(k=>panels[k].opened===true)];
        let container = openPanel.$container.get(0);
        let target = {x: container.clientWidth/2-zoom.pos.x,
                      y: container.clientHeight/2-zoom.pos.y};
        zoom.zoomTo(target, parseFloat($(ev.target).val())-zoom.scale);
    });
    $('#zoom-reset').on('click', function(ev) {
        zoom.reset();
	    $('#zoom-range').val(zoom.scale);
    });
});
