<template>
</template>

<script>
import { LineBase } from '../../src/editor/mixins.js';

export default Vue.extend({
    mixins: [LineBase],
    computed: {
        showregion() {
            let idx = this.$store.state.lines.all.indexOf(this.line);
            if (idx) {
                let pr = this.$store.state.lines.all[idx - 1].region;
                if (this.line.region == pr)
                    return "";
                else
                    return this.getRegion() + 1 ;
            } else {
                return this.getRegion() + 1 ;
            }
        }
    },
    mounted() {
        Vue.nextTick(function() {
            this.$parent.appendLine();
            if (this.line.currentTrans) this.setElContent(this.line.currentTrans.content);
        }.bind(this));

        // load colors, regarding user profile and/or region types
        let beSettings = userProfile.get("baseline-editor-" + this.$store.state.document.id) || {};
        this.regionColors = beSettings["color-regions"] || {};  //  if a coloring attribute exists, will use it
        this.regionTypes =  this.$store.state.document.types.regions.map((t) => t.name);

        // or, create region colors using the same algorithm than for segmentation panel for regions:
        let basicColor = '#11FF76';    // same value used from baseline-editor.js
        for (let index in this.regionTypes) {
            let type = this.regionTypes[index];
            if (this.regionColors[type] == null) {
                this.regionColors[type] = this.changeHue(basicColor, 3*(index+1));
            }
        }

    },
    beforeDestroy() {
        let el = this.getEl();
        if (el != null) {
            el.remove();
        }
    },
    watch: {
        'line.order': function(n, o) {
            // make sure it's at the right place,
            // in case it was just created or the ordering got recalculated
            this.$el.parentNode.insertBefore(
                this.$el,
                this.$el.parentNode.children[this.line.order]);
            this.setElContent(this.line.currentTrans.content);
        },
        'line.currentTrans': function(n, o) {
            if (n!=undefined) {
                this.setElContent(n.content);
            }
        }
    },
    methods: {
        getEl() {
            return this.$parent.$refs.diplomaticLines.querySelector('div:nth-child('+parseInt(this.line.order+1)+')');
        },
        setElContent(content) {
            let line = this.getEl();
            if (line) line.textContent = content;

            // additional code to set/display background-colors when some lines are linked to some specific region type:
            let regionType = this.getRegionType();  //  return the string of the type / null when no region linked
            if(regionType != null){
                let rgb = this.regionColors[regionType];
                let r = rgb[0];
                let g = rgb[1];
                let b = rgb[2];
                let hexa = this.rgb2hex(r,g,b);
                let cmyk = this.rgb2cmyk(r,g,b);
                cmyk = 'cmyk('+cmyk.c+', '+cmyk.m+', '+cmyk.y+', '+cmyk.k+')';   // would give better results and nearest to svg colors but not working
                rgb = "rgb("+r+"," +g+ ","+b+")";

                // desaturate colors: more suitable for backgrounuds when reading
                let sat = 0.6;
                var gray = r * 0.3086 + g * 0.6094 + b * 0.0820;

                r = Math.round(r * sat + gray * (1-sat));
                g = Math.round(g * sat + gray * (1-sat));
                b = Math.round(b * sat + gray * (1-sat));

                let rgba = "rgba("+r+"," +g+ ","+b+", 0.2)";

                line.style.backgroundColor = rgba;  //  possible values: hexa,rgb,rgba (allows opacity),(cmyk)
                // to display the region type by the nav when mouseoverring: - 
                // - could next do this in a more accurate way: 
                // maybe display a semi-transparent fixed div, disappearing after few second and reappearing when scrolling, for example -
                line.title = regionType;
            }

        },
        getRegion() {
            return this.$store.state.regions.all.findIndex(r => r.pk == this.line.region);
        },
        getRegionType() {
            let regions = this.$store.state.regions.all;
            for(var i = 0; i < regions.length; i++)
            {
                var r = regions[i];
                if(r.pk == this.line.region){
                    return r.type;
                }
            }
            return null;    //  no linked region type has been found
        },
        // coloring computation methods (one sample from basline-editor methods):
        changeHue(rgb, degree) {
            // exepcts a string and returns an object
            function rgbToHSL(rgb) {
                // strip the leading # if it's there
                rgb = rgb.replace(/^\s*#|\s*$/g, '');

                // convert 3 char codes --> 6, e.g. `E0F` --> `EE00FF`
                if(rgb.length == 3){
                    rgb = rgb.replace(/(.)/g, '$1$1');
                }

                var r = parseInt(rgb.substr(0, 2), 16) / 255,
                    g = parseInt(rgb.substr(2, 2), 16) / 255,
                    b = parseInt(rgb.substr(4, 2), 16) / 255,
                    cMax = Math.max(r, g, b),
                    cMin = Math.min(r, g, b),
                    delta = cMax - cMin,
                    l = (cMax + cMin) / 2,
                    h = 0,
                    s = 0;

                if (delta == 0) {
                    h = 0;
                }
                else if (cMax == r) {
                    h = 60 * (((g - b) / delta) % 6);
                }
                else if (cMax == g) {
                    h = 60 * (((b - r) / delta) + 2);
                }
                else {
                    h = 60 * (((r - g) / delta) + 4);
                }

                if (delta == 0) {
                    s = 0;
                }
                else {
                    s = (delta/(1-Math.abs(2*l - 1)))
                }

                return {
                    h: h,
                    s: s,
                    l: l
                }
            }

            // expects an object and returns a string
            function hslToRGB(hsl) {
                var h = hsl.h,
                    s = hsl.s,
                    l = hsl.l,
                    c = (1 - Math.abs(2*l - 1)) * s,
                    x = c * ( 1 - Math.abs((h / 60 ) % 2 - 1 )),
                    m = l - c/ 2,
                    r, g, b;

                if (h < 60) {
                    r = c;
                    g = x;
                    b = 0;
                }
                else if (h < 120) {
                    r = x;
                    g = c;
                    b = 0;
                }
                else if (h < 180) {
                    r = 0;
                    g = c;
                    b = x;
                }
                else if (h < 240) {
                    r = 0;
                    g = x;
                    b = c;
                }
                else if (h < 300) {
                    r = x;
                    g = 0;
                    b = c;
                }
                else {
                    r = c;
                    g = 0;
                    b = x;
                }

                r = normalize_rgb_value(r, m);
                g = normalize_rgb_value(g, m);
                b = normalize_rgb_value(b, m);

                // return rgb2hex(r,g,b);
                return [r,g,b];
            }

            function normalize_rgb_value(color, m) {
                color = Math.floor((color + m) * 255);
                if (color < 0) {
                    color = 0;
                }
                return color;
            }

            var hsl = rgbToHSL(rgb);
            hsl.h += degree;
            if (hsl.h > 360) {
                hsl.h -= 360;
            }
            else if (hsl.h < 0) {
                hsl.h += 360;
            }
            return hslToRGB(hsl);
        },

        rgb2hex(r, g, b) {
            return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
        },

        rgb2cmyk(r, g, b, normalized){
            var c = 1 - (r / 255);
            var m = 1 - (g / 255);
            var y = 1 - (b / 255);
            var k = Math.min(c, Math.min(m, y));
            
            c = (c - k) / (1 - k);
            m = (m - k) / (1 - k);
            y = (y - k) / (1 - k);
            
            if(!normalized){
                c = Math.round(c * 10000) / 100;
                m = Math.round(m * 10000) / 100;
                y = Math.round(y * 10000) / 100;
                k = Math.round(k * 10000) / 100;
            }
            
            c = isNaN(c) ? 0 : c;
            m = isNaN(m) ? 0 : m;
            y = isNaN(y) ? 0 : y;
            k = isNaN(k) ? 0 : k;
            
            return {
                c: Math.round(c)+'%',
                m: Math.round(m)+'%',
                y: Math.round(y)+'%',
                k: Math.round(k)+'%'
            }
        }
    }
});
</script>

<style scoped>
</style>
