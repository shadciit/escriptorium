<template>
  <div class="row">
    <div class="col-12 col-sm-4 col-md-3 col-lg-2">

      <div class="accordion">
        <div class="title">
            <h3>{% trans "Tags" %}</h3>
        </div>

        <div class="item item-accordion" id="item1">
            <h2>Document tags</h2>
            <i class="fas fa-chevron-down" id="j" v-on:click="animatefunction('j')"></i>
            <div class="info" id="info-j">
              <ul class="clearfix ckeckbox-list">
                  <li v-for="tagd in tags">
                    <div class="checkbox">
                      <input v-if="parseliststr(tagd.id)" type="checkbox" class="filterdoc" id="{{tagd.id}}" v-on:click="getFilterDocument" name="categorytag-{{tagd.category}}" checked>
                      <input v-else type="checkbox" class="filterdoc" id="{{tagd.id}}" v-on:click="getFilterDocument" name="categorytag-{{tagd.category}}">
                    
                      <label for="{{tagd.id}}"><span class="badge badge-pill badge-{{tagd.priority | color_on_tag}}">{{tagd.name}}</span></label>
                    </div>
                  </li>
            </ul>
            </div>
        </div>

        <div class="item item-accordion" id="item2">
            <h2>Document-part tags</h2>
            <i class="fas fa-chevron-down" id="p"></i>
            <div class="info" id="info-p">
                <ul class="clearfix ckeckbox-list">
                    <li v-for="tagi in tagsimg">
                      <div class="checkbox">
                        <input type="checkbox" class="filterdoc" id="{{tagi.id}}" name="{{tagdi.id}}">
                        <label for="{{tagi.id}}"><span class="badge badge-pill badge-{{tagi.priority | color_on_tag}}">{{tagi.name}}</span></label>
                      </div>
                    </li>
              </ul>
            </div>
        </div>

        <div class="item item-accordion">
            <div style="margin-bottom: -10px;" id="item3S">
              <div class="row" style="margin-left: auto; margin-right: auto;">
                <div class="col-6"><h6 id="selectall" v-on:click="toggleselect('true')">Select all </h6></div>
                <div class="col-6"><h6 id="deselectall" v-on:click="toggleselect('false')">Deselect all </h6></div>
              </div>
              
            </div>
            
        </div>

      </div>


    </div>

  </div>
</template>

<script>

export default {
    props: [
        'tags',
        'tagsimg',
        'chainflt',
    ],
    methods: {
        IsNullOrEmptyOrUdf(s){
            if ((s != "") && (s != " ") && (s != null) && (typeof s !== 'undefined')) return true;
            else return false;
        },
        animatefunction(idd){
            $('#info-' + idd).slideToggle(300);
            $('#' + idd).toggleClass("rotate");
        },
        launchmodal(idd){
            e.preventDefault();
            $('#docid').val(idd);
        },
        buildAutoComplete(doc){
            $.ajax({
                type: 'GET',
                url: '/api/documentstags/gettags/',
                data: {
                document: doc
                },
                success (result, statut){ 
                let tabvalues = [];
                result.result.forEach(function(item){
                    let itemval = {label: item.label, value: item.value+'',};
                    tabvalues.push(itemval);
                });
                console.log('tabvalues');
                console.log(tabvalues);
                $('.lremovetags').html('');
                this.instanceAutocomplete = new SelectPure(".lremovetags", {
                    options: tabvalues,
                    autocomplete: true,
                    multiple: true,
                    icon: "fa fa-times",
                    onChange: value => { console.log(value); },
                    classNames: {
                    select: "select-pure__select",
                    dropdownShown: "select-pure__select--opened",
                    multiselect: "select-pure__select--multiple",
                    label: "select-pure__label",
                    placeholder: "select-pure__placeholder",
                    dropdown: "select-pure__options",
                    option: "select-pure__option",
                    autocompleteInput: "select-pure__autocomplete",
                    selectedLabel: "select-pure__selected-label",
                    selectedOption: "select-pure__option--selected",
                    placeholderHidden: "select-pure__placeholder--hidden",
                    optionHidden: "select-pure__option--hidden",
                    }
                });
                }
            });
        },
        launchmodalunassign(idd){
            $('#docidrmv').val(idd);
            this.docid = idd;
            this.buildAutoComplete(idd);
            setTimeout(() => {
                $("#tagRemoveModal").modal('show');
            }, 1000);
        },
        getTabFilters(value){
            let tab = [];
            $.each($("input[name='" + value + "']:checked"), function(){
                tab.push($(this).attr('id'));
            });
            return tab;
        },
        getFilterDocument(){
        //let chainfilter = getTabFilters('categorytag-D').join(',') + '¤' + getTabFilters('categorytag-P').join(',');
        let chainfilter = this.getTabFilters('categorytag-D').join(',');
        let baseUrlDoc = '/documents/'
        if(this.IsNullOrEmptyOrUdf(chainfilter)){
            let url = baseUrlDoc + chainfilter + '/filter/'
            document.location.href = url;
        }
        else {
            document.location.href = baseUrlDoc;
        }
        },
        activateFields(tab, bool){
            tab.forEach(function(item){
                $('#'+item).attr('disabled', bool);
            });
        },
        resetTagsList(tab, bool){
            this.instanceAutocomplete.reset();
        },
        toggleselect(bool){
            $.each($("input.filterdoc:checkbox"), function(){
                $(this).prop('checked', bool);
            });
            this.getFilterDocument();
        },
        removetaglist(){
            $.ajax({
                type: 'get',
                url: '/api/documentstags/unassign/',
                data: {
                    document: this.docid,
                    tags: this.instanceAutocomplete.value().join(',')
                },
                success (result, statut){ 
                    document.location.reload();
                }
            });
        },
        parseliststr(idd){
            return (this.chainflt.split(',').includes(idd)) ? true : false;
        }
    }
}

</script>