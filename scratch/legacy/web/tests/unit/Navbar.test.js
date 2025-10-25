import { mount, flushPromises } from '@vue/test-utils'
import { beforeAll, afterAll, afterEach } from 'vitest'
import { createTestingPinia } from '@pinia/testing'
import { server } from '../../mocks/msw/server'

import { createVuetify } from "vuetify";
import axios from 'axios'

import { world_list_response, world_info_response } from '../../mocks/msw/handlers'
import { useStore } from '../../src/store'
import Navbar from '../../src/components/AppNavbar.vue'
import SecretDialog from "../../src/components/SecretDialog.vue";

const DEFAULT_WORLD = process.env.VITE_APP_DEFAULT_WORLD;

describe('Navbar Component', async () => {

    beforeAll(() => server.listen()) // Start the server at the beginning of your tests
    afterEach(() => server.resetHandlers()) // Reset any runtime request handlers
    afterAll(() => server.close()) // Clean up after your tests are done


    // Mount the component
    let wrapper = mount(Navbar, {'global':
            {'plugins':
                [createVuetify(),
                createTestingPinia(
                    {
                        // initialState: {
                        //     main: {current_world_uid: "abc"}
                        // },
                        stubActions: false,
                        // createSpy: vi.fn
                    },
                )] }
    }
    )
    const store = useStore()
    // await wrapper.vm.$nextTick()

    // Test 1: Check if the title is rendered correctly
    it('renders the title', () => {
        expect(wrapper.text()).toContain('WebTangl')
    })

    // // Test 2: Check if the API call is made
    // it('fetches the list of worlds on mount', () => {
    //     console.log(mock.history)
    //     expect(mock).toHaveBeenCalledWith('/world/ls')
    // })

    it('axios can fetch and put', async () => {
        let response = await axios.get('/world/ls')
        expect(response.data).toEqual(world_list_response)

        response = await axios.put('/user/world', {'uid': 'abc'})
        console.log(response.data.uid)
    }
    );

    it('sets the default world and the store mirrors the vm.store', async () =>{
        console.log( 'default world', DEFAULT_WORLD )
        expect( DEFAULT_WORLD ).toBeDefined()

        expect( store.current_world_uid ).toBe( wrapper.vm.store.current_world_uid )
        expect( store.current_world_uid ).toBe( DEFAULT_WORLD )
        console.log( store.current_world_info )
        expect( store.current_world_info).toEqual( world_info_response )

        expect(store.setCurrentWorld).toHaveBeenCalledTimes(1)

        store.setCurrentWorld("def")
        expect( store.current_world_uid ).toBe( "def" )
    })

    it('updates the current world and makes a PUT request when a world is clicked', async () => {

        console.log( 'before click', store.current_world_uid )

        // Simulate a click on the _second_ world in the 1st dropdown menu
        const menu_items = wrapper.get('#worldsMenu').findAll('v-list-item');
        console.log( menu_items[1] )  // ldr1
        await menu_items[1].trigger('click')
        await flushPromises()
        expect(store.setCurrentWorld).toHaveBeenCalledTimes(3)
        console.log( 'after click world', store.current_world_uid )
        // Check that the current world updated to the clicked world
        expect(store.current_world_uid).toBe(wrapper.vm.worlds[1].uid);

        // Check that the interface and content refreshed
        // todo: This depends on how we implement the refresh
    });

    test('updates secret', async () => {

        const secret_dialog = wrapper.getComponent(SecretDialog)
        console.log( secret_dialog )
        expect(secret_dialog.dialog_open).toBe(false);

        // Simulate a click on the 1st item of the user menu
        const menu_items = wrapper.get('#userMenu').findAll( 'v-list-item' )
        console.log( menu_items[0] )
        await menu_items[0].trigger('click');
        await wrapper.vm.$nextTick()
        expect(secret_dialog.dialog_open).toBe(true);

        // Enter a secret and click the Use Secret button
        wrapper.vm.secret = 'my secret';
        const button = wrapper.get('#useSecret')
        console.log( button )
        await button.trigger('click');
        await wrapper.vm.$nextTick()
        expect(store.setUserSecret).toHaveBeenCalledWith('my secret');
        await flushPromises()
        expect(store.user_api_key).toBe('ABCDE');
    });


})
