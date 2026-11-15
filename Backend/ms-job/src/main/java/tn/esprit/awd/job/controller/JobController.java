package tn.esprit.awd.job.controller;

import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;
import tn.esprit.awd.job.dto.JobRequest;
import tn.esprit.awd.job.dto.JobResponse;
import tn.esprit.awd.job.service.JobService;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/jobs")
public class JobController {

    private final JobService jobService;

    public JobController(JobService jobService) {
        this.jobService = jobService;
    }

    @GetMapping
    public List<JobResponse> findAll(
            @RequestParam(required = false) Boolean available,
            @RequestParam(required = false) Long categoryId) {
        return jobService.search(available, categoryId);
    }

    @GetMapping("/{id}")
    public JobResponse findById(@PathVariable Long id) {
        return jobService.findById(id);
    }

    @PostMapping
    public ResponseEntity<JobResponse> create(@Valid @RequestBody JobRequest request) {
        JobResponse created = jobService.create(request);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}").buildAndExpand(created.id()).toUri();
        return ResponseEntity.created(location).body(created);
    }

    @PutMapping("/{id}")
    public JobResponse update(@PathVariable Long id, @Valid @RequestBody JobRequest request) {
        return jobService.update(id, request);
    }

    @PatchMapping("/{id}/availability")
    public JobResponse setAvailability(@PathVariable Long id, @RequestParam boolean available) {
        return jobService.setAvailability(id, available);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        jobService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
