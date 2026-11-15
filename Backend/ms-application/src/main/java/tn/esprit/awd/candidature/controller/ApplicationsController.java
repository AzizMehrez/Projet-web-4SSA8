package tn.esprit.awd.candidature.controller;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Positive;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;
import tn.esprit.awd.candidature.dto.ApplicationDto;
import tn.esprit.awd.candidature.service.ApplicationService;

import java.util.List;

@RestController
@RequestMapping("/api/applications")
public class ApplicationsController {
    private final ApplicationService service;

    public ApplicationsController(ApplicationService service) {
        this.service = service;
    }

    @GetMapping
    public List<ApplicationDto> list(@RequestParam(required = false) @Positive Long candidateId,
                                     @RequestParam(required = false) @Positive Long jobId,
                                     @PageableDefault(sort = "id") Pageable pageable) {
        return service.list(candidateId, jobId, pageable);
    }

    @GetMapping("/{id}")
    public ApplicationDto get(@PathVariable @Positive Long id) {
        return service.get(id);
    }

    @PostMapping
    public ResponseEntity<ApplicationDto> create(@Valid @RequestBody ApplicationDto.Create request) {
        var application = service.create(request);
        var location = ServletUriComponentsBuilder.fromCurrentRequest().path("/{id}")
                .buildAndExpand(application.id()).toUri();
        return ResponseEntity.created(location).body(application);
    }

    @PutMapping("/{id}")
    public ApplicationDto update(@PathVariable @Positive Long id, @Valid @RequestBody ApplicationDto.Update request) {
        return service.update(id, request);
    }

    @PatchMapping("/{id}")
    public ApplicationDto changeStatus(@PathVariable @Positive Long id,
                                       @Valid @RequestBody ApplicationDto.StatusUpdate request) {
        return service.changeStatus(id, request);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable @Positive Long id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }

    @ExceptionHandler({org.springframework.dao.DataIntegrityViolationException.class,
            org.springframework.dao.OptimisticLockingFailureException.class})
    public org.springframework.http.ProblemDetail conflict() {
        return org.springframework.http.ProblemDetail.forStatusAndDetail(
                org.springframework.http.HttpStatus.CONFLICT, "Application already exists or changed concurrently");
    }
}
