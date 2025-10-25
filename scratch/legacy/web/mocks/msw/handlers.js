// handlers.js
import { rest } from 'msw'

const block1 = {
    uid: 'block1_uid',
    title: 'A new scene!',
    text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Urna neque viverra justo nec ultrices. Lacinia quis vel eros donec ac.',
    dialog: [
        {
            text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit'
        }, {
            text: "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.  Urna neque viverra justo nec ultrices. Lacinia quis vel eros donec ac. Tellus in metus vulputate eu scelerisque felis.",
            label: "pov",
            style: {color: "rgb(var(--v-theme-primary))", opacity: 0.9},
        }, {
            text: "Id volutpat lacus laoreet non curabitur gravida arcu ac.",
            label: "girl",
            style: {color: 'cornflowerblue', opacity: 0.9},
            media: [
                { media_role: 'avatar_im',
                  url: "https://picsum.photos/200"}
                ]
        }, {
            text: "Scelerisque varius morbi enim nunc. Et magnis dis parturient montes nascetur ridiculus mus. Nisl tincidunt eget nullam non nisi est sit. Diam maecenas sed enim ut sem. Auctor urna nunc id cursus metus. Aliquet enim tortor at auctor urna nunc. Quis commodo odio aenean sed adipiscing diam."
        }],
    media: [
        { media_role: 'narrative_im',
          url: "https://picsum.photos/1200/400",
          orientation: 'landscape' }
    ]
}

const block2 = {
    uid: 'block2_uid',
    text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Urna neque viverra justo nec ultrices. Lacinia quis vel eros donec ac. Tellus in metus vulputate eu scelerisque felis. Id volutpat lacus laoreet non curabitur gravida arcu ac. Scelerisque varius morbi enim nunc. Et magnis dis parturient montes nascetur ridiculus mus. Nisl tincidunt eget nullam non nisi est sit. Diam maecenas sed enim ut sem. Auctor urna nunc id cursus metus. Aliquet enim tortor at auctor urna nunc. Quis commodo odio aenean sed adipiscing diam.',
    media: [ {
        media_role: 'narrative_im',
        url: "https://picsum.photos/300/400",
        orientation: 'portrait'}
    ],
    actions: [
        {uid: "action1", text: 'Make choice1', icon: 'emoticon-happy'},
        {uid: "action2", text: 'Make choice2'}
    ]
}

const block3 = {
    uid: 'block3_uid',
    text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Urna neque viverra justo nec ultrices. Lacinia quis vel eros donec ac. Tellus in metus vulputate eu scelerisque felis. Id volutpat lacus laoreet non curabitur gravida arcu ac. Scelerisque varius morbi enim nunc. Et magnis dis parturient montes nascetur ridiculus mus. Nisl tincidunt eget nullam non nisi est sit. Diam maecenas sed enim ut sem. Auctor urna nunc id cursus metus. Aliquet enim tortor at auctor urna nunc. Quis commodo odio aenean sed adipiscing diam.',
    media: [
        { media_role: 'narrative_im',
          url: "https://source.unsplash.com/random/600x600?city,night",
          orientation: 'square' }
    ],
    actions: [
        {uid: "action1", text: 'Make choice1', icon: 'emoticon-sad'},
        {uid: "action2", text: 'Make choice2'}
    ]
}

export const story_update_response = [ block1, block2 ]
export const story_do_response = [ block3 ]

export const world_list_response = [
    { 'key': 'tst1',
      'style': {'color': 'green'},
      'value': 'Test Story Script'},
     {'key': 'tst2',
      'style': {'color': 'blue'},
      'value': 'Test Story Script'},
     {'key': 'tst3',
      'style': {'color': 'yellow'},
      'value': 'Test Story Script'}
]

export const status_response = [{
    key: 'status',
    value: 'working',
    style: {color: 'red'}
},{
    key: 'another item',
    value: 'also working!',
    style: {color: 'green'}
},{
    key: 'unstyled',
    value: 'foo!',
}
]

export const world_info_response = {
    'title': 'My world!',
    'version': '2.7.9',
    'summary': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Urna neque viverra justo nec ultrices. Lacinia quis vel eros donec ac. Tellus in metus vulputate eu scelerisque felis. Id volutpat lacus laoreet non curabitur gravida arcu ac. Scelerisque varius morbi enim nunc. Et magnis dis parturient montes nascetur ridiculus mus. Nisl tincidunt eget nullam non nisi est sit. Diam maecenas sed enim ut sem. Auctor urna nunc id cursus metus. Aliquet enim tortor at auctor urna nunc. Quis commodo odio aenean sed adipiscing diam.',
    'author': ["tangldev", "others"],
    'date': "Spring, 2023",
    'media': [
        { 'media_role': 'banner_im', "url": "https://source.unsplash.com/random/1200x200?city,night" },
        { 'media_role': 'info_im', "url": "https://source.unsplash.com/random/1200x800?city,night" },
        { 'media_role': 'logo_im', "url": "https://source.unsplash.com/random/200x200?city,night" }
    ],
    'ui_config': {'brand_color': 'green'},
}

export const system_info_response = {
    'api_url': "https://api.storytan.gl/api/v2",
    'version': "3.0.1",
    'homepage_url': "https://git.storytan.gl/tangldev/storytan.gl",
    'active_users': 2,
    'uptime': "2 hour",
    'media': [
        {'media_role': 'info_im', 'url': "https://source.unsplash.com/random/1200x800?computer" }
    ]
}

export const handlers = [

    rest.get('/story/update', (req, res, ctx) => {
        return res(
            ctx.status(200),
            ctx.json( story_update_response )
        )
    }),

    rest.post('/story/do', (req, res, ctx) => {
        return res(
            ctx.status(200),
            ctx.json( story_do_response )
        )
    }),

    rest.get('/story/status', (req, res, ctx) => {
        return res(
            ctx.status(200),
            ctx.json( status_response )
        )
    }),

    rest.put('/user/world', (req, res, ctx) => {
        return res(
            ctx.status(200),
            ctx.json(
                story_update_response,
            )
        )
    }),
    rest.put('/user/secret', (req, res, ctx) => {
        return res(
            ctx.status(200),
            ctx.json(
                {api_key: "ABCDE", 'secret': req.body.secret},
            )
        )
    }),

    rest.get('/system/worlds', (req, res, ctx) => {
        return res(
            ctx.status(200),
            ctx.json( world_list_response )
        )
    }),

    rest.get( `/world/*/info`, (req, res, ctx) => {
        return res(
            ctx.status(200),
            ctx.json( world_info_response )
        )
    }),

    rest.get( `/system/info`, (req, res, ctx) => {
        return res(
            ctx.status(200),
            ctx.json( system_info_response )
        )
    })

    // ...other handlers for 'user/go', 'user/secret', etc.
]
