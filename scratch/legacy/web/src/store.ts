import { defineStore } from 'pinia'
import axios from 'axios'
import { WorldInfo } from "@/types";
import { useGlobal } from "@/globals"
const { makeMediaDict } = useGlobal()

export const useStore = defineStore({
    id: 'main',
    state: () => ({
        current_world_uid: import.meta.env.VITE_DEFAULT_WORLD,
        current_world_info: undefined as WorldInfo,
        // order: check loadable, check env, req from api, fallback
        user_secret: import.meta.env.VITE_DEFAULT_USER_SECRET,
    }),
    actions: {
        async setCurrentWorld(world_uid) {
            this.$patch( {current_world_uid: world_uid} );
            this.getCurrentWorldInfo()
        },
        async getCurrentWorldInfo() {
            const response = await axios.get<WorldInfo>(`/world/${this.current_world_uid}/info`);

            // Check if the response data has a media list and transform it
            if(response.data && response.data.media) {
                response.data.media_dict = makeMediaDict(response.data);
            }
            this.$patch( {current_world_info: response.data } )
        },
        async getApiKey() {
            // Request DOES NOT update the secret
            const response = await axios.get( '/system/secret', {params: {secret: this.user_secret}})
            if (response.data.secret !== this.user_secret) {
                console.error('Failed to get key for secret')
            } else {
                axios.defaults.headers['X-Api-Key'] = response.data.api_key
                this.$patch({user_api_key: response.data.api_key})
            }
        },
        async setApiKey(secret: string) {
            // Request DOES update the user's API key
            const response = await axios.put('/user/secret', { secret: secret })
            axios.defaults.headers['X-Api-Key'] = response.data.api_key
            // Save the secret locally
            this.$patch( {
                user_secret: response.data.secret,
                user_api_key: response.data.api_key} );
            }
        }
    }
)
