class Panel {
    constructor ($panel, $tools, opened) {
        this.$panel = $panel;
        this.$tools = $tools;
        this.opened = opened | false;
        this.$container = $('.img-container', this.$panel);
        
        window.addEventListener('resize', function() {
            this.refresh();
        }.bind(this));
    }
    
    load(part) {
        this.part = part;
        this.api = API.part.replace('{part_pk}', this.part.pk);
	    if (this.opened) this.open();
	}
    
    open() {
        this.opened = true;
        this.$panel.show(0, this.onShow.bind(this));
        this.$tools.show(0);
        Cookies.set(this.$panel.attr('id'), true, {expires: 30});
    }
    
    close() {
        this.opened = false;
        this.$panel.hide();
        this.$tools.hide();
        Cookies.set(this.$panel.attr('id'), false);
    }
    
    toggle() {
        if (this.opened) this.close();
        else this.open();
    }
    
    refresh() {}  // usually: data didn't change but some context did
    reset() {}  // usually: restart from scratch
    onShow() {}
}
