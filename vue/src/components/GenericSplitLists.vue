<template>
  <div id="app" style="margin-bottom: 4vh">

    <div class="row">
      <div class="col-md-2 d-none d-md-block">
      </div>
      <div class="col-xl-8 col-12">
        <div class="container-fluid d-flex flex-column flex-grow-1" :class="{'vh-100' : show_split}">
          <!-- expanded options box -->
          <div class="row flex-shrink-0">
            <div class="col col-md-12">
              <b-collapse id="collapse_advanced" class="mt-2" v-model="advanced_visible">
                <div class="card">
                  <div class="card-body">
                    <div class="row">
                      <div class="col-md-3" style="margin-top: 1vh">
                       <div class="btn btn-primary btn-block text-uppercase" @click="$emit('item-action', {'action':'new'})">
                            {{ this.text.new }}
                          </div>
                      </div>

                      <div class="col-md-3" style="margin-top: 1vh">
                        <button class="btn btn-primary btn-block text-uppercase" @click="resetSearch">
                          {{ this.text.reset }}
                        </button>
                      </div>
                      <div class="col-md-3" style="position: relative; margin-top: 1vh">
                        <b-form-checkbox v-model="show_split" name="check-button"
                                        class="shadow-none"
                                        style="position:relative;top: 50%;  transform: translateY(-50%);" switch>
                          {{ this.text.split }}
                        </b-form-checkbox>
                      </div>
                    </div>

                  </div>
                </div>
              </b-collapse>
            </div>
          </div>

          <div class="row flex-shrink-0">
            <!-- search box -->
            <div class="col col-md">
              <b-input-group class="mt-3">
                <b-input class="form-control" v-model="search_left" 
                        v-bind:placeholder="this.text.search"></b-input>
                <b-input-group-append>
                  <b-button v-b-toggle.collapse_advanced variant="primary" class="shadow-none">
                    <i class="fas fa-caret-down" v-if="!advanced_visible"></i>
                    <i class="fas fa-caret-up"  v-if="advanced_visible"></i>
                  </b-button>
                </b-input-group-append>
              </b-input-group>
            </div>

            <!-- split side search -->
            <div class="col col-md" v-if="show_split">
              <b-input-group class="mt-3">
                <b-input class="form-control" v-model="search_right" 
                        v-bind:placeholder="this.text.search"></b-input>
              </b-input-group>
            </div>
          </div>

          <!-- only show scollbars in split mode -->
          <!-- TODO: weird behavior when switching to split mode, infinite scoll doesn't trigger if 
                bottom of page is in viewport can trigger by scrolling page (not column) up  -->
          <div class="row" :class="{'overflow-hidden' : show_split}">
            <div class="col col-md" :class="{'mh-100 overflow-auto' : show_split}">
              <slot name="cards-left"></slot>
              <infinite-loading
                :identifier='left' 
                @infinite="infiniteHandler($event, 'left')" 
                spinner="waveDots">
                <template v-slot:no-more><span/></template>
                <template v-slot:no-results><span>{{$t('No_Results')}}</span></template>
              </infinite-loading>
            </div>
            <!-- right side cards -->
            <div class="col col-md mh-100 overflow-auto" v-if="show_split">
              <slot name="cards-right"></slot>
              <infinite-loading
                :identifier='right' 
                @infinite="infiniteHandler($event, 'right')" 
                spinner="waveDots">
                <template v-slot:no-more><span/></template>
                <template v-slot:no-results><span>{{$t('No_Results')}}</span></template>
              </infinite-loading>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-2 d-none d-md-block">
      </div>
    </div>
  </div>
</template>

<script>
import 'bootstrap-vue/dist/bootstrap-vue.css'
import _debounce from 'lodash/debounce'
import InfiniteLoading from 'vue-infinite-loading';

export default {
  // TODO: this should be simplified into a Generic Infinitely Scrolling List and added as two components when split lists desired
  name: 'GenericSplitLists',
  components: {InfiniteLoading},
  props: {
    list_name: {type: String, default: 'Blank List'},  // TODO update translations to handle plural translations
    left_list: {type: Array, default(){return []}},
    left_counts: {type: Object},
    right_list: {type:Array, default(){return []}},
    right_counts: {type: Object},
  },
  data() {
    return {
      advanced_visible: false,
      show_split: false,
      search_right: '',
      search_left: '',
      right_page: 0,
      left_page: 0,
      right_state: undefined,
      left_state: undefined,
      right_dirty: false,
      left_dirty: false,
      right: +new Date(),
      left: +new Date(),
      text: {
          'new': '',
          'name': '',
          'reset': this.$t('Reset_Search'),
          'split': this.$t('show_split_screen'),
          'search': this.$t('Search')
      },
    }
  },
  mounted() {
    this.dragMenu = this.$refs.tooltip
    this.text.new = this.$t('New_' + this.list_name)
  },
  watch: {
    search_left: _debounce(function() {
      if (this.left_dirty) {
        //prevents running twice if search is reset
        this.left_dirty = false
        return
      }
      this.left_page = 0
      this.$emit('reset', {'column':'left'})
      this.left += 1
    }, 700),
    search_right: _debounce(function(newVal, oldVal) {
      if (this.right_dirty) {
        //prevents running twice if search is reset
        this.right_dirty = false
        return
      }
      this.right_page = 0
      this.$emit('reset', {'column':'right'})
      this.right += 1
    }, 700),
    right_counts: {
      deep: true,
      handler(newVal, oldVal) {
        if (newVal.current > 0) {
          this.right_state.loaded()
        }
        if (newVal.current >= newVal.max) {
          this.right_state.complete()
        }
      }
    },
    left_counts: {
      deep: true,
      handler(newVal, oldVal) {
        if (newVal.current > 0) {
          this.left_state.loaded()
        }
        if (newVal.current >= newVal.max) {
          this.left_state.complete()
        }
      }
    }
  },
  methods: {
    resetSearch: function () {
        this.right_dirty = true
        this.search_right = ''
        this.right_page = 0
        this.right += 1
        this.$emit('reset', {'column':'right'})

        this.left_dirty = true
        this.search_left = ''
        this.left_page = 0
        this.left += 1
        this.$emit('reset', {'column':'left'})
    },
    infiniteHandler: function($state, col) { 
        let params = {
            'query': (col==='left') ? this.search_left : this.search_right,
            'page': (col==='left') ? this.left_page + 1 : this.right_page + 1,
            'column': col
        }
        this[col+'_state'] = $state
        this.$emit('get-list', params)
        this[col+'_page'] += 1
    },
  }
}

</script>

<style src="vue-multiselect/dist/vue-multiselect.min.css"></style>

<style>

</style>
