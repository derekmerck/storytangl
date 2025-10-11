Voice Audio (vox)
=================

A cue sheet looks like this:

```yaml
media:
  audio: abc.mp3  # for merged

cues:
  - time: 0.0     # for merged
    text:
      "Hi I'm actor1"
    role:
      actor: my_actor1
      attitude: happy
      outfit: blue
    audio:  # for serial audio files
      abc.mp3      
    staging:
      im: actor.portrait
      does: bottom rt -> bottom rmid, 2s
      
  - time: 2.0
    text:
      "Hi there, my_actor1!"
    role:
      actor: my_actor2
      attitude: glum
      outfit: carwash
    staging:
      - im: my_actor2.portrait
        does: bottom lt -> bottom lmid, 2s

```

# Scene 1

```
my_actor1:
  outfit: blue
  attitude: happy
my_actor2:
  outfit: carwash
  attitude: happy
```

![im: actor1]{rt->rmid, 2s}
> [!my_actor1.sad] Dialog Header
> I'm so happy, my_actor2

> [!my_actor1.sad] Dialog Header
> Hi there my_actor1!