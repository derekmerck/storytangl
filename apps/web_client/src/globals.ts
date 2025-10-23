// useGlobal.js
import { ref } from 'vue'
import axios from 'axios'

export function useGlobal() {
    const $http = ref(axios)
    const $debug = ref(process.env.NODE_ENV === 'development')
    const $verbose = ref( import.meta.env.VITE_SHOW_RESPONSES === 'true')

    const remapURL = (url) => {
      // Check if the URL is relative
      if (!url.startsWith('http')) {
          const base_url = new URL($http.value.defaults.baseURL);
          const protocol = base_url.protocol; // "https:"
          const hostname = base_url.hostname; // "example.com"
          const port = base_url.port; // "8000"
          const server = `${protocol}//${hostname}:${port}`
          return server + url
      }
      return url
    }

    const makeMediaDict = (obj, mediaKey = 'media') => {
        if (!obj.hasOwnProperty(mediaKey)) {
            console.warn(`makeMediaDict: Object does not have key ${mediaKey}`);
            return {};
        }
        const mediaList = obj[mediaKey];
        return mediaList.reduce((acc, item) => {
            acc[item.media_role] = item;
            acc[item.media_role].url = remapURL(item.url)
            return acc;
        }, {});
    };

    return {
        $http,
        $debug,
        $verbose,
        remapURL,
        makeMediaDict
    }
}